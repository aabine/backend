from prometheus_client import Counter, Histogram, Gauge
from functools import wraps
import time
import logging

logger = logging.getLogger(__name__)

# HTTP Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# Database Metrics
db_connections_active = Gauge(
    'db_connections_active',
    'Number of active database connections'
)

db_operation_duration_seconds = Histogram(
    'db_operation_duration_seconds',
    'Database operation duration',
    ['operation']
)

# Cache Metrics
cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

# AI Service Metrics
ai_requests_total = Counter(
    'ai_requests_total',
    'Total AI API requests',
    ['operation']
)

ai_request_duration_seconds = Histogram(
    'ai_request_duration_seconds',
    'AI request duration'
)

ai_error_counter = Counter(
    'ai_errors_total',
    'Total AI API errors',
    ['operation', 'error_type']
)

def monitor_http_request():
    """Decorator to monitor HTTP requests."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            method = kwargs.get('request').method
            endpoint = kwargs.get('request').url.path
            start_time = time.time()
            
            try:
                response = await func(*args, **kwargs)
                status = response.status_code
                return response
            except Exception as e:
                status = 500
                raise
            finally:
                duration = time.time() - start_time
                http_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status=status
                ).inc()
                http_request_duration_seconds.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(duration)
        return wrapper
    return decorator

def monitor_db_operation(operation: str):
    """Decorator to monitor database operations."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                db_operation_duration_seconds.labels(
                    operation=operation
                ).observe(duration)
        return wrapper
    return decorator

class MetricsCollector:
    @staticmethod
    def record_cache_hit(cache_type: str):
        cache_hits_total.labels(cache_type=cache_type).inc()
    
    @staticmethod
    def record_cache_miss(cache_type: str):
        cache_misses_total.labels(cache_type=cache_type).inc()
    
    @staticmethod
    def record_db_connection(active: bool):
        if active:
            db_connections_active.inc()
        else:
            db_connections_active.dec()
    
    @staticmethod
    def record_ai_request(operation: str, duration: float, error: str = None):
        ai_requests_total.labels(operation=operation).inc()
        ai_request_duration_seconds.observe(duration)
        if error:
            ai_error_counter.labels(
                operation=operation,
                error_type=error
            ).inc() 