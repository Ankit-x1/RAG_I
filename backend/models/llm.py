"""
Language Model interface using Groq API.

This module handles text generation using Groq's fast inference API.
"""

import logging
from typing import List, Dict, Optional
from groq import Groq

from backend.models.config import RAGConfig

logger = logging.getLogger(__name__)


class LLMGenerator:
    """Generate responses using Groq LLM."""

    def __init__(self, config: RAGConfig):
        """
        Initialize the LLM generator.

        Args:
            config: RAG configuration containing Groq settings.
        """
        self.config = config
        if not config.groq.api_key:
            raise ValueError("GROQ_API_KEY not set in environment variables")
        
        self.client = Groq(api_key=config.groq.api_key)
        self.model = config.groq.model

    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate text using Groq.

        Args:
            prompt: The prompt to send to the model.
            temperature: Temperature for generation (0-2).
            max_tokens: Maximum tokens in the response.

        Returns:
            Generated text response.
        """
        try:
            temperature = temperature or self.config.groq.temperature
            max_tokens = max_tokens or self.config.groq.max_tokens

            message = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            response = message.choices[0].message.content
            logger.info(f"Generated response with {len(response)} characters")
            return response

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

    def generate_with_context(
        self,
        query: str,
        context_chunks: List[Dict],
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate a response using retrieved context.

        Args:
            query: The user's query.
            context_chunks: Retrieved document chunks.
            system_prompt: Optional system prompt to override default.

        Returns:
            Generated response grounded in the context.
        """
        # Create context string from chunks
        context_text = self._format_context(context_chunks)

        # Create the augmented prompt
        if system_prompt is None:
            system_prompt = self._get_default_system_prompt()

        augmented_prompt = f"""{system_prompt}

## Context
{context_text}

## User Query
{query}

## Response"""

        logger.info(f"Generating response for query: {query[:50]}...")
        return self.generate(augmented_prompt)

    def _format_context(self, chunks: List[Dict]) -> str:
        """Format retrieved chunks into readable context."""
        if not chunks:
            return "No relevant context found."

        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            part = f"""
Source {i}: {chunk.get('title', 'Unknown')}
Section: {chunk.get('section', 'N/A')}
URL: {chunk.get('url', 'N/A')}
Content: {chunk.get('text', '')}
Relevance Score: {chunk.get('score', 0):.2f}
"""
            context_parts.append(part)

        return "\n".join(context_parts)

    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt for RAG."""
        return """You are a helpful assistant that answers questions based on provided context documents.
Use the context provided to answer the user's question accurately and comprehensively.
If the context doesn't contain relevant information, say so clearly.
Always cite your sources by mentioning the relevant document sections and URLs.
Be concise but thorough in your responses."""

    def chat_with_history(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a response in a multi-turn conversation.

        Args:
            messages: List of message dictionaries with 'role' and 'content'.
            temperature: Temperature for generation.
            max_tokens: Maximum tokens in the response.

        Returns:
            Generated response.
        """
        try:
            temperature = temperature or self.config.groq.temperature
            max_tokens = max_tokens or self.config.groq.max_tokens

            response = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error in chat generation: {e}")
            raise
