"""
Backend utilities module.
Contains caching, production utilities, monitoring, and helpers.
"""

from .cache import (
    EmbeddingCache,
    QueryCache,
    embedding_cache,
    query_cache,
    get_embedding_cache,
    get_query_cache
)

from .production import (
    StructuredLogger,
    get_logger,
    PerformanceMonitor,
    performance_monitor,
    track_performance,
    RAGException,
    RetrievalException,
    GenerationException,
    EmbeddingException,
    ConfigurationException,
    handle_exception,
    HealthChecker,
    health_checker,
    format_response,
    format_error_response,
    batch_process,
    MetricsExporter,
    metrics_exporter
)

__all__ = [
    # Caching
    'EmbeddingCache',
    'QueryCache',
    'embedding_cache',
    'query_cache',
    'get_embedding_cache',
    'get_query_cache',
    # Logging & Monitoring
    'StructuredLogger',
    'get_logger',
    'PerformanceMonitor',
    'performance_monitor',
    'track_performance',
    # Error Handling
    'RAGException',
    'RetrievalException',
    'GenerationException',
    'EmbeddingException',
    'ConfigurationException',
    'handle_exception',
    # Health Checks
    'HealthChecker',
    'health_checker',
    # Response Formatting
    'format_response',
    'format_error_response',
    # Batch Processing
    'batch_process',
    # Metrics
    'MetricsExporter',
    'metrics_exporter'
]
