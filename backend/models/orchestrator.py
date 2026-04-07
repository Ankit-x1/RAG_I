"""
RAG Orchestrator - Coordinates the entire RAG pipeline.

This module manages:
- Indexing pipeline execution
- RAG agent lifecycle
- Error handling and logging
- Pipeline status and metrics
"""

import asyncio
import logging
from typing import Optional, Dict
from datetime import datetime
from enum import Enum

from backend.models.config import RAGConfig
from backend.models.agent import RAGAgent
from backend.indexing.pipeline import run_indexing

logger = logging.getLogger(__name__)


class PipelineState(Enum):
    """States for the indexing pipeline."""
    IDLE = "idle"
    INDEXING = "indexing"
    COMPLETED = "completed"
    ERROR = "error"
    PAUSED = "paused"


class RAGOrchestrator:
    """
    Orchestrates the complete RAG system including indexing and querying.
    
    Responsibilities:
    - Manage indexing pipeline lifecycle
    - Coordinate RAG agent
    - Track system metrics
    - Handle errors gracefully
    """

    def __init__(self, config: Optional[RAGConfig] = None):
        """
        Initialize the orchestrator.

        Args:
            config: RAG configuration. If None, loads from environment.
        """
        self.config = config or RAGConfig.from_env()
        self.rag_agent = RAGAgent(self.config)
        
        # Pipeline state tracking
        self.pipeline_state = PipelineState.IDLE
        self.last_index_time: Optional[datetime] = None
        self.total_indexed_documents = 0
        self.total_indexed_chunks = 0
        
        # Error tracking
        self.last_error: Optional[str] = None
        self.error_count = 0
        
        logger.info("RAG Orchestrator initialized")

    async def start_indexing(self, force: bool = False) -> Dict:
        """
        Start the indexing pipeline.

        Args:
            force: If True, re-index even if already indexed.

        Returns:
            Status dictionary with indexing information.
        """
        if self.pipeline_state == PipelineState.INDEXING:
            return {
                "status": "already_running",
                "message": "Indexing pipeline is already running",
            }

        self.pipeline_state = PipelineState.INDEXING
        self.last_error = None

        try:
            logger.info("Starting indexing pipeline...")
            await run_indexing()
            
            self.pipeline_state = PipelineState.COMPLETED
            self.last_index_time = datetime.now()
            
            logger.info("Indexing pipeline completed successfully")
            
            return {
                "status": "completed",
                "message": "Indexing pipeline completed successfully",
                "timestamp": self.last_index_time.isoformat(),
            }

        except Exception as e:
            self.pipeline_state = PipelineState.ERROR
            self.last_error = str(e)
            self.error_count += 1
            
            logger.error(f"Indexing pipeline failed: {e}")
            
            return {
                "status": "error",
                "message": f"Indexing pipeline failed: {str(e)}",
                "error": str(e),
                "error_count": self.error_count,
            }

    def query(self, question: str, top_k: Optional[int] = None) -> Dict:
        """
        Process a RAG query.

        Args:
            question: The user's question.
            top_k: Number of documents to retrieve.

        Returns:
            Query result as dictionary.
        """
        try:
            result = self.rag_agent.query(question, top_k=top_k)
            return {
                "status": "success",
                "query": result.query,
                "response": result.response,
                "sources": result.retrieved_chunks,
                "metadata": result.metadata,
            }
        except Exception as e:
            logger.error(f"Query failed: {e}")
            self.error_count += 1
            return {
                "status": "error",
                "message": f"Query failed: {str(e)}",
                "error": str(e),
            }

    def get_metrics(self) -> Dict:
        """Get system metrics and statistics."""
        agent_status = self.rag_agent.get_status()
        
        return {
            "system_status": {
                "pipeline_state": self.pipeline_state.value,
                "last_index_time": (
                    self.last_index_time.isoformat() if self.last_index_time else None
                ),
                "error_count": self.error_count,
                "last_error": self.last_error,
            },
            "agent_metrics": {
                "queries_processed": agent_status["queries_processed"],
                "conversation_turns": agent_status["conversation_turns"],
            },
            "collection_metrics": agent_status.get("collection", {}),
            "configuration": agent_status.get("configuration", {}),
        }

    def reset(self) -> None:
        """Reset the orchestrator to initial state."""
        self.rag_agent.reset()
        self.pipeline_state = PipelineState.IDLE
        self.last_index_time = None
        self.last_error = None
        self.error_count = 0
        logger.info("RAG Orchestrator reset")

    def chat(self, message: str) -> Dict:
        """
        Process a chat message.

        Args:
            message: User's message.

        Returns:
            Chat response as dictionary.
        """
        try:
            response = self.rag_agent.chat(message)
            return {
                "status": "success",
                "message": message,
                "response": response,
            }
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            self.error_count += 1
            return {
                "status": "error",
                "message": f"Chat failed: {str(e)}",
                "error": str(e),
            }

    def health_check(self) -> Dict:
        """Perform a health check on the system."""
        try:
            collection_info = self.rag_agent.retriever.get_collection_info()
            
            return {
                "status": "healthy",
                "rag_agent": "ready",
                "collection": collection_info is not None,
                "pipeline_state": self.pipeline_state.value,
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
            }
