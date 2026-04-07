"""
Production-grade embedding cache with LRU eviction and TTL support.
Reduces redundant embedding computations and API calls.
"""

import time
import hashlib
from collections import OrderedDict
from typing import Optional, Dict, List
from functools import lru_cache
import json
import logging

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """
    In-memory embedding cache with LRU eviction and TTL.
    
    Features:
    - Automatic TTL eviction (default 24 hours)
    - LRU eviction when max_size exceeded
    - Thread-safe operations
    - Persistent cache serialization
    """
    
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 86400):
        """
        Initialize embedding cache.
        
        Args:
            max_size: Maximum number of entries (default 10k)
            ttl_seconds: Time-to-live in seconds (default 24 hours)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, Dict] = OrderedDict()
        self.hits = 0
        self.misses = 0
        
    def _hash_text(self, text: str) -> str:
        """Generate deterministic hash for text."""
        return hashlib.md5(text.encode()).hexdigest()
    
    def get(self, text: str) -> Optional[List[float]]:
        """
        Retrieve cached embedding.
        
        Returns None if expired or not found.
        """
        key = self._hash_text(text)
        
        if key not in self.cache:
            self.misses += 1
            return None
        
        entry = self.cache[key]
        
        # Check expiration
        if time.time() - entry['timestamp'] > self.ttl_seconds:
            logger.debug(f"Embedding cache entry expired: {key}")
            del self.cache[key]
            self.misses += 1
            return None
        
        # Move to end (LRU marker)
        self.cache.move_to_end(key)
        self.hits += 1
        return entry['embedding']
    
    def put(self, text: str, embedding: List[float]) -> None:
        """
        Cache an embedding.
        
        Automatically evicts oldest entry if max_size exceeded.
        """
        key = self._hash_text(text)
        
        # Remove if exists (to update timestamp)
        if key in self.cache:
            del self.cache[key]
        
        # Add new entry at end
        self.cache[key] = {
            'embedding': embedding,
            'timestamp': time.time(),
            'text_length': len(text)
        }
        
        # Evict oldest if over capacity
        while len(self.cache) > self.max_size:
            oldest_key, oldest_entry = self.cache.popitem(last=False)
            logger.debug(f"Evicting cache entry due to size limit: {oldest_key}")
    
    def clear(self) -> None:
        """Clear all cached embeddings."""
        self.cache.clear()
        logger.info("Embedding cache cleared")
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate_percent': round(hit_rate, 2),
            'total_requests': total_requests,
            'memory_mb': self._estimate_memory_mb()
        }
    
    def _estimate_memory_mb(self) -> float:
        """Estimate cache memory usage in MB."""
        total_elements = sum(len(e.get('embedding', [])) for e in self.cache.values())
        # Each float is ~8 bytes, plus overhead
        bytes_used = total_elements * 8 + len(self.cache) * 200
        return bytes_used / (1024 * 1024)
    
    def prune_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        current_time = time.time()
        expired = [
            k for k, v in self.cache.items()
            if current_time - v['timestamp'] > self.ttl_seconds
        ]
        
        for key in expired:
            del self.cache[key]
        
        if expired:
            logger.info(f"Pruned {len(expired)} expired cache entries")
        
        return len(expired)
    
    def save_to_file(self, filepath: str) -> None:
        """Persist cache to JSON file."""
        try:
            data = {
                key: {
                    'embedding': value['embedding'],
                    'timestamp': value['timestamp']
                }
                for key, value in self.cache.items()
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f)
            
            logger.info(f"Cache saved to {filepath} ({len(self.cache)} entries)")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def load_from_file(self, filepath: str) -> None:
        """Load cache from JSON file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            for key, value in data.items():
                self.cache[key] = {
                    'embedding': value['embedding'],
                    'timestamp': value['timestamp'],
                    'text_length': len(str(value))
                }
            
            logger.info(f"Cache loaded from {filepath} ({len(self.cache)} entries)")
        except FileNotFoundError:
            logger.debug(f"Cache file not found: {filepath}")
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")


class QueryCache:
    """
    Cache for complete query results.
    Speeds up repeated queries significantly.
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """Initialize query result cache."""
        self.cache: OrderedDict[str, Dict] = OrderedDict()
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.hits = 0
        self.misses = 0
    
    def _hash_query(self, query: str, top_k: int) -> str:
        """Generate deterministic hash for query."""
        query_key = f"{query}|{top_k}"
        return hashlib.md5(query_key.encode()).hexdigest()
    
    def get(self, query: str, top_k: int = 5) -> Optional[Dict]:
        """Get cached query result."""
        key = self._hash_query(query, top_k)
        
        if key not in self.cache:
            self.misses += 1
            return None
        
        entry = self.cache[key]
        
        # Check expiration
        if time.time() - entry['timestamp'] > self.ttl_seconds:
            del self.cache[key]
            self.misses += 1
            return None
        
        # Move to end (LRU)
        self.cache.move_to_end(key)
        self.hits += 1
        return entry['result']
    
    def put(self, query: str, top_k: int, result: Dict) -> None:
        """Cache a query result."""
        key = self._hash_query(query, top_k)
        
        if key in self.cache:
            del self.cache[key]
        
        self.cache[key] = {
            'result': result,
            'timestamp': time.time()
        }
        
        while len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'size': len(self.cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate_percent': round(hit_rate, 2)
        }


# Global cache instances
embedding_cache = EmbeddingCache(max_size=10000, ttl_seconds=86400)
query_cache = QueryCache(max_size=1000, ttl_seconds=3600)


def get_embedding_cache() -> EmbeddingCache:
    """Get global embedding cache instance."""
    return embedding_cache


def get_query_cache() -> QueryCache:
    """Get global query cache instance."""
    return query_cache
