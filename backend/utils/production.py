"""
Production utilities: logging, monitoring, error handling, metrics.
Ensures enterprise-grade observability and reliability.
"""

import logging
import time
import json
from typing import Dict, Any, Callable
from datetime import datetime
from functools import wraps
import traceback

# === Structured Logging ===

class StructuredLogger:
    """Production-grade structured logging with JSON output."""
    
    def __init__(self, name: str, level: str = "INFO"):
        """Initialize structured logger."""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level))
        
        # JSON formatter
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def _log(self, level: str, message: str, **context) -> None:
        """Log structured message with context."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'message': message,
            **context
        }
        
        log_method = getattr(self.logger, level.lower())
        log_method(json.dumps(log_data))
    
    def info(self, message: str, **context) -> None:
        """Log info level."""
        self._log('INFO', message, **context)
    
    def error(self, message: str, **context) -> None:
        """Log error level."""
        self._log('ERROR', message, **context)
    
    def warning(self, message: str, **context) -> None:
        """Log warning level."""
        self._log('WARNING', message, **context)
    
    def debug(self, message: str, **context) -> None:
        """Log debug level."""
        self._log('DEBUG', message, **context)


def get_logger(name: str, level: str = "INFO") -> StructuredLogger:
    """Get a configured logger instance."""
    return StructuredLogger(name, level)


# === Performance Monitoring ===

class PerformanceMonitor:
    """Track API performance metrics."""
    
    def __init__(self):
        """Initialize performance monitor."""
        self.metrics = {
            'total_requests': 0,
            'total_time_ms': 0,
            'errors': 0,
            'operations': {}
        }
    
    def record_operation(self, operation: str, duration_ms: float, success: bool = True) -> None:
        """Record operation metrics."""
        if operation not in self.metrics['operations']:
            self.metrics['operations'][operation] = {
                'count': 0,
                'total_time_ms': 0,
                'errors': 0,
                'avg_time_ms': 0,
                'min_time_ms': float('inf'),
                'max_time_ms': 0
            }
        
        op = self.metrics['operations'][operation]
        op['count'] += 1
        op['total_time_ms'] += duration_ms
        op['avg_time_ms'] = op['total_time_ms'] / op['count']
        op['min_time_ms'] = min(op['min_time_ms'], duration_ms)
        op['max_time_ms'] = max(op['max_time_ms'], duration_ms)
        
        if not success:
            op['errors'] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all tracked metrics."""
        return {
            **self.metrics,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def reset(self) -> None:
        """Reset all metrics."""
        self.metrics = {
            'total_requests': 0,
            'total_time_ms': 0,
            'errors': 0,
            'operations': {}
        }


# Global monitor instance
performance_monitor = PerformanceMonitor()


def track_performance(operation_name: str = None) -> Callable:
    """Decorator to track function performance."""
    def decorator(func: Callable) -> Callable:
        op_name = operation_name or func.__name__
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                performance_monitor.record_operation(op_name, duration_ms, success=True)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                performance_monitor.record_operation(op_name, duration_ms, success=False)
                raise
        
        return wrapper
    return decorator


# === Error Handling ===

class RAGException(Exception):
    """Base exception for RAG system."""
    
    def __init__(self, message: str, error_code: str = "RAG_ERROR", details: Dict = None):
        """Initialize RAG exception."""
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary."""
        return {
            'error': self.message,
            'error_code': self.error_code,
            'details': self.details,
            'timestamp': datetime.utcnow().isoformat()
        }


class RetrievalException(RAGException):
    """Exception during document retrieval."""
    pass


class GenerationException(RAGException):
    """Exception during response generation."""
    pass


class EmbeddingException(RAGException):
    """Exception during embedding generation."""
    pass


class ConfigurationException(RAGException):
    """Exception in configuration."""
    pass


def handle_exception(exc: Exception, logger: StructuredLogger = None) -> Dict[str, Any]:
    """
    Handle exception with logging and structured response.
    
    Args:
        exc: The exception to handle
        logger: Optional logger instance
    
    Returns:
        Structured error response
    """
    error_dict = {
        'error': str(exc),
        'error_type': type(exc).__name__,
        'timestamp': datetime.utcnow().isoformat(),
        'traceback': traceback.format_exc()
    }
    
    if isinstance(exc, RAGException):
        error_dict.update(exc.to_dict())
    
    if logger:
        logger.error(
            f"Exception: {type(exc).__name__}",
            error=str(exc),
            error_type=type(exc).__name__
        )
    
    return error_dict


# === Health Checks ===

class HealthChecker:
    """Monitor system health and dependencies."""
    
    def __init__(self):
        """Initialize health checker."""
        self.checks = {}
    
    def register_check(self, name: str, check_func: Callable) -> None:
        """Register a health check."""
        self.checks[name] = check_func
    
    async def check_all(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }
        
        for name, check_func in self.checks.items():
            try:
                if hasattr(check_func, '__call__'):
                    result = check_func()
                    results['checks'][name] = {
                        'status': 'healthy' if result else 'unhealthy',
                        'result': result
                    }
            except Exception as e:
                results['checks'][name] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
        
        # Overall status
        results['overall_status'] = 'healthy' if all(
            c.get('status') == 'healthy' for c in results['checks'].values()
        ) else 'unhealthy'
        
        return results


health_checker = HealthChecker()


# === Request/Response Formatting ===

def format_response(
    data: Any = None,
    status: str = "success",
    message: str = "",
    metadata: Dict = None
) -> Dict[str, Any]:
    """Format API response with metadata."""
    return {
        'status': status,
        'data': data,
        'message': message,
        'timestamp': datetime.utcnow().isoformat(),
        'metadata': metadata or {}
    }


def format_error_response(
    error: str,
    status_code: int = 500,
    error_code: str = "INTERNAL_ERROR",
    details: Dict = None
) -> Dict[str, Any]:
    """Format error response."""
    return {
        'status': 'error',
        'error': error,
        'error_code': error_code,
        'status_code': status_code,
        'details': details or {},
        'timestamp': datetime.utcnow().isoformat()
    }


# === Batch Processing ===

def batch_process(
    items: list,
    processor: Callable,
    batch_size: int = 32,
    logger: StructuredLogger = None
) -> list:
    """
    Process items in batches with error handling.
    
    Args:
        items: Items to process
        processor: Processing function
        batch_size: Size of each batch
        logger: Optional logger
    
    Returns:
        List of processed results
    """
    results = []
    total_batches = (len(items) + batch_size - 1) // batch_size
    
    for batch_idx in range(0, len(items), batch_size):
        batch = items[batch_idx:batch_idx + batch_size]
        batch_num = batch_idx // batch_size + 1
        
        try:
            if logger:
                logger.info(
                    f"Processing batch {batch_num}/{total_batches}",
                    batch_size=len(batch)
                )
            
            batch_results = processor(batch)
            results.extend(batch_results)
        
        except Exception as e:
            if logger:
                logger.error(
                    f"Error processing batch {batch_num}",
                    error=str(e)
                )
            raise
    
    return results


# === Metrics Export ===

class MetricsExporter:
    """Export metrics in Prometheus format."""
    
    def __init__(self):
        """Initialize metrics exporter."""
        self.metrics = {}
    
    def add_metric(self, name: str, value: float, labels: Dict = None) -> None:
        """Add a metric."""
        key = f"{name}_{str(labels)}" if labels else name
        self.metrics[key] = {
            'name': name,
            'value': value,
            'labels': labels or {},
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        for name, metric in self.metrics.items():
            labels = ','.join(f'{k}="{v}"' for k, v in metric['labels'].items())
            label_str = f"{{{labels}}}" if labels else ""
            lines.append(f"{metric['name']}{label_str} {metric['value']}")
        
        return "\n".join(lines)


# Global metrics exporter
metrics_exporter = MetricsExporter()
