"""
RAG Agent - Orchestrates the complete Retrieval-Augmented Generation pipeline.

This module handles the full RAG workflow: retrieve relevant context,
generate responses, and manage the conversation state.
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from backend.models.config import RAGConfig
from backend.models.retriever import Retriever
from backend.models.llm import LLMGenerator

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result of a RAG query."""
    query: str
    response: str
    retrieved_chunks: List[Dict]
    metadata: Dict


class RAGAgent:
    """
    Complete RAG agent for answering questions with retrieved context.
    
    Pipeline:
    1. Accept a query
    2. Retrieve relevant chunks from vector database
    3. Generate response using LLM with retrieved context
    4. Return response with citations
    """

    def __init__(self, config: Optional[RAGConfig] = None):
        """
        Initialize the RAG agent.

        Args:
            config: RAG configuration. If None, loads from environment.
        """
        self.config = config or RAGConfig.from_env()
        
        # Initialize components
        self.retriever = Retriever(self.config)
        self.llm = LLMGenerator(self.config)
        
        # Conversation history for multi-turn interactions
        self.conversation_history: List[Dict[str, str]] = []
        self.query_count = 0
        
        logger.info("RAG Agent initialized successfully")

    def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        use_history: bool = True,
    ) -> QueryResult:
        """
        Process a user query and return an augmented response.

        Args:
            question: The user's question.
            top_k: Number of documents to retrieve.
            use_history: Whether to use conversation history.

        Returns:
            QueryResult with response and metadata.
        """
        self.query_count += 1
        logger.info(f"Processing query #{self.query_count}: {question[:50]}...")

        try:
            # Step 1: Retrieve relevant chunks
            retrieved_chunks = self.retriever.retrieve(question, top_k=top_k)
            
            if not retrieved_chunks:
                logger.warning("No relevant chunks retrieved")
                response = "I couldn't find relevant information to answer your question."
                retrieved_chunks = []
            else:
                # Step 2: Generate response with context
                response = self.llm.generate_with_context(question, retrieved_chunks)

            # Step 3: Add to conversation history
            if use_history:
                self.conversation_history.append({"role": "user", "content": question})
                self.conversation_history.append({"role": "assistant", "content": response})

            # Step 4: Create result
            result = QueryResult(
                query=question,
                response=response,
                retrieved_chunks=retrieved_chunks,
                metadata={
                    "query_number": self.query_count,
                    "timestamp": datetime.now().isoformat(),
                    "chunks_retrieved": len(retrieved_chunks),
                    "avg_relevance_score": (
                        sum(c["score"] for c in retrieved_chunks) / len(retrieved_chunks)
                        if retrieved_chunks else 0
                    ),
                },
            )

            logger.info(f"Query processed successfully with {len(retrieved_chunks)} chunks")
            return result

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            raise

    def batch_query(self, questions: List[str]) -> List[QueryResult]:
        """
        Process multiple queries.

        Args:
            questions: List of questions to answer.

        Returns:
            List of QueryResults.
        """
        results = []
        for question in questions:
            results.append(self.query(question))
        return results

    def chat(self, message: str, system_prompt: Optional[str] = None) -> str:
        """
        Have a multi-turn conversation with context awareness.

        Args:
            message: User's message.
            system_prompt: Optional custom system prompt.

        Returns:
            Assistant's response.
        """
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": message})

        try:
            # Retrieve context for the current message
            retrieved_chunks = self.retriever.retrieve(message)

            # If we have context, use RAG-augmented chat
            if retrieved_chunks:
                response = self.llm.generate_with_context(
                    message,
                    retrieved_chunks,
                    system_prompt=system_prompt,
                )
            else:
                # Otherwise, use regular chat without context
                response = self.llm.chat_with_history(self.conversation_history)

            # Add assistant response to history
            self.conversation_history.append({"role": "assistant", "content": response})

            return response

        except Exception as e:
            logger.error(f"Error in chat: {e}")
            raise

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")

    def get_status(self) -> Dict:
        """Get current agent status."""
        collection_info = self.retriever.get_collection_info()
        
        return {
            "status": "active",
            "queries_processed": self.query_count,
            "collection": collection_info,
            "conversation_turns": len(self.conversation_history),
            "configuration": {
                "top_k_retrieval": self.config.top_k_retrieval,
                "similarity_threshold": self.config.similarity_threshold,
                "llm_model": self.config.groq.model,
            },
        }

    def reset(self) -> None:
        """Reset the agent to initial state."""
        self.clear_history()
        self.query_count = 0
        logger.info("RAG Agent reset")
