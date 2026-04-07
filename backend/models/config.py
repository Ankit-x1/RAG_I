"""
Configuration management for the RAG system.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class QdrantConfig:
    """Configuration for Qdrant vector database."""
    host: str = os.getenv("QDRANT_HOST", "localhost")
    port: int = int(os.getenv("QDRANT_PORT", "6333"))
    collection_name: str = os.getenv("QDRANT_COLLECTION", "fastapi_docs")
    vector_size: int = 384  # sentence-transformers/all-MiniLM-L6-v2


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""
    model_name: str = os.getenv(
        "EMBEDDING_MODEL", 
        "sentence-transformers/all-MiniLM-L6-v2"
    )
    batch_size: int = 32


@dataclass
class GroqConfig:
    """Configuration for Groq LLM."""
    api_key: str = os.getenv("GROQ_API_KEY", "")
    model: str = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")
    max_tokens: int = int(os.getenv("GROQ_MAX_TOKENS", "1024"))
    temperature: float = float(os.getenv("GROQ_TEMPERATURE", "0.7"))


@dataclass
class RAGConfig:
    """Configuration for the RAG system."""
    qdrant: QdrantConfig
    embedding: EmbeddingConfig
    groq: GroqConfig
    
    # Retrieval parameters
    top_k_retrieval: int = int(os.getenv("RAG_TOP_K", "5"))
    similarity_threshold: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.5"))
    
    # Indexing parameters
    checkpoint_file: str = os.getenv("CHECKPOINT_FILE", "data/processed/last_indexed.json")
    upload_batch_size: int = int(os.getenv("UPLOAD_BATCH_SIZE", "100"))
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def from_env(cls) -> "RAGConfig":
        """Create config from environment variables."""
        return cls(
            qdrant=QdrantConfig(),
            embedding=EmbeddingConfig(),
            groq=GroqConfig(),
        )
