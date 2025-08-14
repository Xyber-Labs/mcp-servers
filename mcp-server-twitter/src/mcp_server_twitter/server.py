import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import re

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel

from .twitter import AsyncTwitterClient, get_twitter_client
from mcp_server_twitter.logging_config import configure_logging
from .helpers import classify_tweet_type
import functools


configure_logging()
logger = logging.getLogger(__name__)
print(f"🔥 LOADING SERVER FROM: {__file__}")

from .exceptions import (
    BaseMCPException, 
    ServiceUnavailableError, 
    InvalidResponseError, 
    AuthenticationError, 
    ValidationError, 
    RateLimitError
)

# --- Performance Metrics --- #
@dataclass
class PerformanceMetrics:
    """Track performance statistics for operations."""
    request_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    request_latencies: list = field(default_factory=list)
    operations: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    operation_latencies: Dict[str, list] = field(default_factory=lambda: defaultdict(list))
    operation_errors: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def average_latency_ms(self) -> float:
        """Calculate average request latency."""
        if self.request_count == 0:
            return 0.0
        return self.total_latency_ms / self.request_count

    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage."""
        if self.request_count == 0:
            return 0.0
        return (self.error_count / self.request_count) * 100

    def get_operation_stats(self, operation: str) -> Dict[str, Any]:
        """Get statistics for a specific operation."""
        latencies = self.operation_latencies[operation]
        if not latencies:
            return {
                "count": 0,
                "error_count": 0,
                "average_latency_ms": 0.0,
                "min_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "error_rate": 0.0
            }
        
        count = self.operations[operation]
        errors = self.operation_errors[operation]
        
        return {
            "count": count,
            "error_count": errors,
            "average_latency_ms": round(sum(latencies) / len(latencies), 2),
            "min_latency_ms": round(min(latencies), 2),
            "max_latency_ms": round(max(latencies), 2),
            "error_rate": round((errors / count) * 100, 2) if count > 0 else 0.0
        }

# Global metrics instance
performance_metrics = PerformanceMetrics()

# Global Twitter client
twitter_client: Optional[AsyncTwitterClient] = None

# --- Data Sanitization --- #
SENSITIVE_PATTERNS = [
    r'\b[A-Za-z0-9]{20,}\b',  # Potential API keys/tokens
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email addresses
    r'bearer\s+[A-Za-z0-9._=-]+',  # Bearer tokens
    r'token["\s:=]+[A-Za-z0-9._=-]+',  # Token values
]

def sanitize_sensitive_data(text: str) -> str:
    """Remove sensitive information from text."""
    sanitized = text
    for pattern in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
    return sanitized

# --- FastAPI Middleware --- #
class PerformanceMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware to track performance metrics."""
    
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        # Store request_id in request state for use in endpoints
        request.state.request_id = request_id
        
        # Increment request counters
        performance_metrics.request_count += 1
        
        # Log request start
        logger.info("HTTP request started", extra={
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "status": "START",
            "middleware": "performance_tracking",
            "total_requests": performance_metrics.request_count
        })
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate latency
            end_time = time.time()
            latency_ms = round((end_time - start_time) * 1000, 2)
            
            # Record successful request metrics
            performance_metrics.total_latency_ms += latency_ms
            performance_metrics.request_latencies.append(latency_ms)
            
            # Log successful request
            logger.info("HTTP request completed successfully", extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "status_code": response.status_code,
                "status": "SUCCESS",
                "duration_ms": latency_ms,
                "middleware": "performance_tracking",
                "total_requests": performance_metrics.request_count,
                "average_latency_ms": round(performance_metrics.average_latency_ms, 2)
            })
            
            return response
            
        except Exception as e:
            # Calculate latency for failed requests
            end_time = time.time()
            latency_ms = round((end_time - start_time) * 1000, 2)
            
            # Record failed request metrics
            performance_metrics.error_count += 1
            performance_metrics.total_latency_ms += latency_ms
            performance_metrics.request_latencies.append(latency_ms)
            
            # Sanitize error message
            sanitized_error = sanitize_sensitive_data(str(e))
            
            # Log failed request
            logger.error("HTTP request failed", exc_info=True, extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "status": "ERROR",
                "duration_ms": latency_ms,
                "middleware": "performance_tracking",
                "error_type": type(e).__name__,
                "error_message": sanitized_error,
                "total_requests": performance_metrics.request_count,
                "error_count": performance_metrics.error_count,
                "error_rate": round(performance_metrics.error_rate, 2)
            })
            
            # Re-raise the exception
            raise

# --- Request Models --- #
class CreateTweetRequest(BaseModel):
    text: str
    image_content_str: Optional[str] = None
    poll_options: Optional[list[str]] = None
    poll_duration: Optional[int] = None
    in_reply_to_tweet_id: Optional[str] = None
    quote_tweet_id: Optional[str] = None

class SearchTweetsRequest(BaseModel):
    query: str
    max_results: int = 10

class FollowUserRequest(BaseModel):
    user_id: str

class RetweetRequest(BaseModel):
    tweet_id: str

class GetTrendsRequest(BaseModel):
    countries: list[str]
    max_trends: int = 50

# --- Dependency Functions --- #
async def get_twitter_client_dependency() -> AsyncTwitterClient:
    """Dependency to get Twitter client."""
    global twitter_client
    if twitter_client is None:
        raise HTTPException(status_code=500, detail="Twitter client not initialized")
    return twitter_client

def get_request_id(request: Request) -> str:
    """Get request ID from request state."""
    return getattr(request.state, 'request_id', 'unknown')


# --- Operation Performance Decorator --- #
def track_operation_performance(operation_name: str):
    """Decorator to track operation-specific performance metrics."""
    def decorator(func):
        @functools.wraps(func)  # This preserves the original function signature!
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Get request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            request_id = getattr(request.state, 'request_id', 'unknown') if request else 'unknown'
            
            # Increment operation counters
            performance_metrics.operations[operation_name] += 1
            
            # Log operation start
            logger.info("Operation started", extra={
                "request_id": request_id,
                "operation": operation_name,
                "status": "START"
            })
            
            try:
                # Execute the operation - pass through args and kwargs directly
                result = await func(*args, **kwargs)
                
                # Calculate latency
                end_time = time.time()
                latency_ms = round((end_time - start_time) * 1000, 2)
                
                # Record successful operation metrics
                performance_metrics.operation_latencies[operation_name].append(latency_ms)
                
                # Log successful operation
                logger.info("Operation completed successfully", extra={
                    "request_id": request_id,
                    "operation": operation_name,
                    "status": "SUCCESS",
                    "duration_ms": latency_ms
                })
                
                return result
                
            except Exception as e:
                # Calculate latency for failed operations
                end_time = time.time()
                latency_ms = round((end_time - start_time) * 1000, 2)
                
                # Record failed operation metrics
                performance_metrics.operation_errors[operation_name] += 1
                performance_metrics.operation_latencies[operation_name].append(latency_ms)
                
                # Sanitize error message
                sanitized_error = sanitize_sensitive_data(str(e))
                
                # Log failed operation
                logger.error("Operation failed", exc_info=True, extra={
                    "request_id": request_id,
                    "operation": operation_name,
                    "status": "ERROR",
                    "duration_ms": latency_ms,
                    "error_type": type(e).__name__,
                    "error_message": sanitized_error
                })
                
                # Re-raise the exception
                raise
                
        return wrapper
    return decorator

# --- Error Handler --- #
def handle_twitter_exceptions(e: Exception) -> BaseMCPException:
    """Convert Twitter API exceptions to custom exceptions with user-friendly messages."""
    error_msg = str(e).lower()
    
    if "rate limit" in error_msg:
        return RateLimitError("Twitter API rate limit exceeded. Please try again later.")
    elif "unauthorized" in error_msg or "401" in error_msg:
        return AuthenticationError("Unauthorized. Please check Twitter API permissions.")
    elif "forbidden" in error_msg or "403" in error_msg:
        return ValidationError("Forbidden. The requested action is not allowed.")
    elif "not found" in error_msg or "404" in error_msg:
        return ValidationError("Resource not found. Please check the provided ID.")
    elif "500" in error_msg or "502" in error_msg or "503" in error_msg:
        return ServiceUnavailableError("Twitter service temporarily unavailable. Please try again later.")
    elif "invalid" in error_msg or "bad request" in error_msg:
        return InvalidResponseError(f"Invalid request: {str(e)}")
    else:
        return BaseMCPException(f"Twitter API error: {str(e)}")

# --- Application Factory --- #
@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """Manage application startup/shutdown."""
    global twitter_client
    initialization_start = time.time()

    logger.info("Application startup: Initializing Twitter client...", extra={
        "operation": "app_startup",
        "status": "START",
        "start_time": initialization_start,
    })
    
    try:
        # Initialize Twitter client
        twitter_client = await get_twitter_client()

        logger.info("Application startup: Twitter client initialization completed", extra={
            "operation": "app_startup",
            "status": "SUCCESS",
            "duration_ms": round((time.time() - initialization_start) * 1000, 2),
        })
        
        yield
        
    except Exception as init_err:
        logger.error("FATAL: Application startup failed", exc_info=True, extra={
            "operation": "app_startup",
            "status": "ERROR",
            "duration_ms": round((time.time() - initialization_start) * 1000, 2),
            "system_error": str(init_err),
            "error_type": type(init_err).__name__
        })
        raise init_err

    finally:
        shutdown_start = time.time()
        
        # Log final performance statistics
        logger.info("Application shutdown: Cleanup completed", extra={
            "operation": "app_shutdown",
            "status": "END",
            "initialization_duration_ms": round((time.time() - initialization_start) * 1000, 2),
            "shutdown_duration_ms": round((time.time() - shutdown_start) * 1000, 2),
            "final_performance_stats": {
                "total_requests": performance_metrics.request_count,
                "total_errors": performance_metrics.error_count,
                "error_rate": round(performance_metrics.error_rate, 2),
                "average_latency_ms": round(performance_metrics.average_latency_ms, 2)
            }
        })

# --- Create FastAPI App --- #
def create_app() -> FastAPI:
    """Create FastAPI application with middleware and routes."""
    app = FastAPI(
        title="Twitter MCP Server",
        description="MCP server for Twitter integration with FastAPI",
        version="2.0.0",
        lifespan=app_lifespan,
    )

    # Add performance middleware
    app.add_middleware(PerformanceMiddleware)
    
    return app

# Create the app instance
app = create_app()

# --- Exception Handlers --- #
@app.exception_handler(BaseMCPException)
async def handle_mcp_exception(request: Request, exc: BaseMCPException):
    """Handle custom MCP exceptions."""
    request_id = get_request_id(request)
    
    logger.error("MCP exception occurred", extra={
        "request_id": request_id,
        "error_code": exc.error_code,
        "error_message": exc.message,
        "error_type": type(exc).__name__
    })
    
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "type": type(exc).__name__
            },
            "request_id": request_id
        }
    )

@app.exception_handler(Exception)
async def handle_general_exception(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    request_id = get_request_id(request)
    sanitized_error = sanitize_sensitive_data(str(exc))
    
    logger.error("Unexpected exception occurred", exc_info=True, extra={
        "request_id": request_id,
        "error_message": sanitized_error,
        "error_type": type(exc).__name__
    })
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "type": "InternalServerError"
            },
            "request_id": request_id
        }
    )

# --- Health Check Endpoint --- #
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "twitter-mcp-server"
    }

# --- Metrics Endpoint --- #
@app.get("/metrics")
async def get_performance_metrics():
    """Get performance metrics."""
    return {
        "performance": {
            "total_requests": performance_metrics.request_count,
            "total_errors": performance_metrics.error_count,
            "error_rate_percent": round(performance_metrics.error_rate, 2),
            "average_latency_ms": round(performance_metrics.average_latency_ms, 2),
            "operations": dict(performance_metrics.operations),
            "operation_stats": {
                op: performance_metrics.get_operation_stats(op) 
                for op in performance_metrics.operations.keys()
            }
        },
        "system": {
            "timestamp": time.time(),
            "server_name": "twitter-server"
        }
    }

# --- Twitter API Endpoints --- #
@app.post("/api/v1/tweets")
@track_operation_performance("create_tweet")
async def create_tweet(
    request: Request,
    tweet_request: CreateTweetRequest,
    client: AsyncTwitterClient = Depends(get_twitter_client_dependency)
):
    """Create a new tweet with optional media, polls, replies or quotes."""
    request_id = get_request_id(request)
    
    logger.info("Processing create tweet request", extra={
        "operation": "create_tweet",
        "status": "START",
        "text_length": len(tweet_request.text),
        "has_image": tweet_request.image_content_str is not None,
        "has_poll": tweet_request.poll_options is not None,
        "is_reply": tweet_request.in_reply_to_tweet_id is not None,
        "is_quote": tweet_request.quote_tweet_id is not None,
        "request_id": request_id
    })

    try:
        result = await client.create_tweet(
            text=tweet_request.text,
            image_content_str=tweet_request.image_content_str,
            poll_options=tweet_request.poll_options,
            poll_duration=tweet_request.poll_duration,
            in_reply_to_tweet_id=tweet_request.in_reply_to_tweet_id,
            quote_tweet_id=tweet_request.quote_tweet_id
        )
        
        return {"result": result, "request_id": request_id}
        
    except Exception as e:
        custom_exception = handle_twitter_exceptions(e)
        raise custom_exception

@app.post("/api/v1/search")
@track_operation_performance("search_tweets")
async def search_tweets(
    request: Request,
    search_request: SearchTweetsRequest,
    client: AsyncTwitterClient = Depends(get_twitter_client_dependency)
):
    """Search for tweets matching the given query."""
    request_id = get_request_id(request)
    
    logger.info("Processing search tweets request", extra={
        "operation": "search_tweets",
        "status": "START",
        "query": search_request.query,
        "max_results": search_request.max_results,
        "request_id": request_id
    })

    try:
        result = await client.search_tweets(
            query=search_request.query,
            max_results=search_request.max_results
        )
        
        return {"result": result, "request_id": request_id}
        
    except Exception as e:
        custom_exception = handle_twitter_exceptions(e)
        raise custom_exception

@app.post("/api/v1/follow")
@track_operation_performance("follow_user")
async def follow_user(
    request: Request,
    follow_request: FollowUserRequest,
    client: AsyncTwitterClient = Depends(get_twitter_client_dependency)
):
    """Follow a user by their user ID."""
    request_id = get_request_id(request)
    
    logger.info("Processing follow user request", extra={
        "operation": "follow_user",
        "status": "START",
        "user_id": follow_request.user_id,
        "request_id": request_id
    })

    try:
        result = await client.follow_user(follow_request.user_id)
        return {"result": result, "request_id": request_id}
        
    except Exception as e:
        custom_exception = handle_twitter_exceptions(e)
        raise custom_exception

@app.post("/api/v1/retweet")
@track_operation_performance("retweet_tweet")
async def retweet_tweet(
    request: Request,
    retweet_request: RetweetRequest,
    client: AsyncTwitterClient = Depends(get_twitter_client_dependency)
):
    """Retweet an existing tweet."""
    request_id = get_request_id(request)
    
    logger.info("Processing retweet request", extra={
        "operation": "retweet_tweet",
        "status": "START",
        "tweet_id": retweet_request.tweet_id,
        "request_id": request_id
    })

    try:
        result = await client.retweet_tweet(retweet_request.tweet_id)
        return {"result": result, "request_id": request_id}
        
    except Exception as e:
        custom_exception = handle_twitter_exceptions(e)
        raise custom_exception

@app.post("/api/v1/trends")
@track_operation_performance("get_trends")
async def get_trends(
    request: Request,
    trends_request: GetTrendsRequest,
    client: AsyncTwitterClient = Depends(get_twitter_client_dependency)
):
    """Get trending topics for specified countries."""
    request_id = get_request_id(request)
    
    logger.info("Processing trends request", extra={
        "operation": "get_trends",
        "status": "START",
        "countries": trends_request.countries,
        "max_trends": trends_request.max_trends,
        "request_id": request_id
    })

    try:
        result = await client.get_trends(
            countries=trends_request.countries,
            max_trends=trends_request.max_trends
        )
        
        return {"result": result, "request_id": request_id}
        
    except Exception as e:
        custom_exception = handle_twitter_exceptions(e)
        raise custom_exception