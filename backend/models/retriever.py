"""
Retriever module for fetching relevant documents from Qdrant.

This module handles retrieval-augmented queries by searching
the vector database for semantically similar chunks.
"""

import logging
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct

from backend.indexing.embedder import EmbeddingGenerator
from backend.models.config import RAGConfig

logger = logging.getLogger(__name__)


class Retriever:
    """Retrieves relevant document chunks from Qdrant vector database."""

    def __init__(self, config: RAGConfig):
        """
        Initialize the retriever.

        Args:
            config: RAG configuration containing Qdrant and embedding settings.
        """
        self.config = config
        self.client = QdrantClient(
            host=config.qdrant.host,
            port=config.qdrant.port,
        )
        self.embedder = EmbeddingGenerator(config.embedding.model_name)
        self.collection_name = config.qdrant.collection_name

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
    ) -> List[Dict]:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: The query string.
            top_k: Number of results to return (defaults to config.top_k_retrieval).
            similarity_threshold: Minimum similarity score (defaults to config.similarity_threshold).

        Returns:
            List of relevant chunks with metadata and scores.
        """
        if not query or not query.strip():
            logger.warning("Empty query provided to retriever")
            return []

        try:
            # Set defaults
            top_k = top_k or self.config.top_k_retrieval
            similarity_threshold = similarity_threshold or self.config.similarity_threshold

            # Embed the query
            query_embedding = self.embedder.embed_batch([query])[0].tolist()

            # Search Qdrant
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=similarity_threshold,
            )

            # Format results
            retrieved_chunks = []
            for result in search_results:
                chunk = {
                    "id": result.id,
                    "text": result.payload.get("text", ""),
                    "url": result.payload.get("url", ""),
                    "title": result.payload.get("title", ""),
                    "section": result.payload.get("section", ""),
                    "score": result.score,
                }
                retrieved_chunks.append(chunk)

            logger.info(
                f"Retrieved {len(retrieved_chunks)} chunks for query: {query[:50]}..."
            )
            return retrieved_chunks

        except Exception as e:
            logger.error(f"Error retrieving chunks: {e}")
            raise

    def batch_retrieve(
        self,
        queries: List[str],
        top_k: Optional[int] = None,
    ) -> Dict[str, List[Dict]]:
        """
        Retrieve relevant chunks for multiple queries.

        Args:
            queries: List of query strings.
            top_k: Number of results per query.

        Returns:
            Dictionary mapping queries to their retrieved chunks.
        """
        results = {}
        for query in queries:
            results[query] = self.retrieve(query, top_k)
        return results

    def check_collection_exists(self) -> bool:
        """Check if the collection exists in Qdrant."""
        try:
            return self.client.collection_exists(self.collection_name)
        except Exception as e:
            logger.error(f"Error checking collection existence: {e}")
            return False

    def get_collection_info(self) -> Optional[Dict]:
        """Get information about the collection."""
        try:
            if not self.check_collection_exists():
                logger.warning(f"Collection '{self.collection_name}' does not exist")
                return None

            collection_info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "points_count": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return None
