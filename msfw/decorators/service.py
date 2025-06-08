"""Service communication decorators for MSFW."""

import asyncio
import functools
from typing import (
    TypeVar, Generic, Optional, Type, Dict, Any, Union, Callable, 
    Awaitable, get_type_hints, get_origin, get_args
)
import inspect
import logging

from pydantic import BaseModel, ValidationError

from msfw.core.types import (
    HTTPMethod, ServiceCallResult, ServiceCallConfig, 
    TypedServiceError, ServiceValidationError,
    RequestT, ResponseT
)
from msfw.sdk import ServiceSDK, sdk


T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

logger = logging.getLogger(__name__)


def service_call(
    service_name: str,
    method: HTTPMethod = HTTPMethod.GET,
    path: str = "",
    config: Optional[ServiceCallConfig] = None,
    auto_unwrap: bool = True
):
    """
    Decorator for type-safe service calls.
    
    Args:
        service_name: Name of the target service
        method: HTTP method to use
        path: API path (can use format strings with function args)
        config: Service call configuration
        auto_unwrap: Automatically unwrap ServiceCallResult
    
    Example:
        @service_call("user-service", HTTPMethod.GET, "/users/{user_id}")
        async def get_user(user_id: int) -> User:
            pass
            
        @service_call("user-service", HTTPMethod.POST, "/users")
        async def create_user(user_data: CreateUserRequest) -> User:
            pass
    """
    call_config = config or ServiceCallConfig()
    
    def decorator(func: F) -> F:
        # Get type hints
        hints = get_type_hints(func)
        sig = inspect.signature(func)
        
        # Determine request and response types
        response_type = hints.get('return', None)
        request_type = None
        
        # Find request model from parameters
        for param_name, param in sig.parameters.items():
            if param_name in hints:
                param_type = hints[param_name]
                if (isinstance(param_type, type) and 
                    issubclass(param_type, BaseModel)):
                    request_type = param_type
                    break
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Get bound arguments
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            
            # Extract request data
            request_data = None
            path_kwargs = {}
            
            for param_name, value in bound.arguments.items():
                if request_type and isinstance(value, request_type):
                    request_data = value.model_dump()
                else:
                    path_kwargs[param_name] = value
            
            # Format path with arguments
            formatted_path = path.format(**path_kwargs) if path_kwargs else path
            
            try:
                # Make service call
                result = await _make_typed_service_call(
                    service_name=service_name,
                    method=method,
                    path=formatted_path,
                    request_data=request_data,
                    response_model=response_type,
                    config=call_config
                )
                
                return result.unwrap() if auto_unwrap else result
                
            except Exception as e:
                logger.error(f"Service call failed in {func.__name__}: {e}")
                raise TypedServiceError(
                    f"Service call to {service_name} failed: {str(e)}",
                    service_name=service_name
                ) from e
        
        # Preserve type information
        wrapper.__annotations__ = func.__annotations__
        return wrapper
    
    return decorator


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to retry function calls on failure.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries
        backoff: Backoff multiplier for delay
        exceptions: Tuple of exceptions to retry on
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed, retrying in {current_delay}s: {e}"
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_attempts} attempts failed")
            
            raise last_exception
        
        return wrapper
    return decorator


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: Type[Exception] = Exception
):
    """
    Circuit breaker decorator.
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Time to wait before trying half-open state
        expected_exception: Exception type that triggers circuit breaker
    """
    def decorator(func: F) -> F:
        # Circuit state tracking
        state = {
            'failures': 0,
            'last_failure_time': 0,
            'state': 'closed'  # closed, open, half-open
        }
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import time
            now = time.time()
            
            # Check circuit state
            if state['state'] == 'open':
                if now - state['last_failure_time'] < recovery_timeout:
                    raise TypedServiceError(
                        "Circuit breaker is open",
                        service_name=func.__name__
                    )
                else:
                    state['state'] = 'half-open'
            
            try:
                result = await func(*args, **kwargs)
                
                # Success - reset circuit
                if state['state'] in ['half-open', 'closed']:
                    state['failures'] = 0
                    state['state'] = 'closed'
                
                return result
                
            except expected_exception as e:
                state['failures'] += 1
                state['last_failure_time'] = now
                
                if state['failures'] >= failure_threshold:
                    state['state'] = 'open'
                    logger.warning(f"Circuit breaker opened for {func.__name__}")
                
                raise
        
        return wrapper
    return decorator


def health_check(
    interval: float = 30.0,
    timeout: float = 5.0,
    failure_threshold: int = 3
):
    """
    Decorator to add health checking to service methods.
    
    Args:
        interval: Health check interval in seconds
        timeout: Health check timeout
        failure_threshold: Number of failures before marking unhealthy
    """
    def decorator(func: F) -> F:
        health_state = {
            'healthy': True,
            'failures': 0,
            'last_check': 0
        }
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import time
            now = time.time()
            
            # Perform health check if needed
            if now - health_state['last_check'] > interval:
                try:
                    # Simple health check - try to call the function with minimal impact
                    await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                    health_state['failures'] = 0
                    health_state['healthy'] = True
                except Exception:
                    health_state['failures'] += 1
                    if health_state['failures'] >= failure_threshold:
                        health_state['healthy'] = False
                finally:
                    health_state['last_check'] = now
            
            # Check if service is healthy
            if not health_state['healthy']:
                raise TypedServiceError(
                    f"Service {func.__name__} is unhealthy",
                    service_name=func.__name__
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def cached_service_call(
    ttl: float = 300.0,  # 5 minutes
    key_func: Optional[Callable[..., str]] = None
):
    """
    Decorator to cache service call results.
    
    Args:
        ttl: Time to live for cache entries in seconds
        key_func: Function to generate cache keys
    """
    cache = {}
    
    def default_key_func(*args, **kwargs):
        return str(hash((args, tuple(sorted(kwargs.items())))))
    
    key_generator = key_func or default_key_func
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import time
            now = time.time()
            
            # Generate cache key
            cache_key = key_generator(*args, **kwargs)
            
            # Check cache
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if now - timestamp < ttl:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return result
                else:
                    del cache[cache_key]
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            cache[cache_key] = (result, now)
            logger.debug(f"Cached result for {func.__name__}")
            
            return result
        
        return wrapper
    return decorator


def service_interface(service_name: str, base_path: str = ""):
    """
    Class decorator to create typed service interfaces.
    
    Example:
        @service_interface("user-service", "/api/v1")
        class UserService:
            @service_call("user-service", HTTPMethod.GET, "/users/{user_id}")
            async def get_user(self, user_id: int) -> User:
                pass
    """
    def decorator(cls):
        cls._service_name = service_name
        cls._base_path = base_path
        
        # Add SDK instance
        if not hasattr(cls, '_sdk'):
            cls._sdk = sdk
        
        return cls
    
    return decorator


async def _make_typed_service_call(
    service_name: str,
    method: HTTPMethod,
    path: str,
    request_data: Optional[Dict[str, Any]] = None,
    response_model: Optional[Type[T]] = None,
    config: ServiceCallConfig = ServiceCallConfig()
) -> ServiceCallResult[T]:
    """Internal function to make typed service calls."""
    
    try:
        # Get SDK instance
        service_sdk = sdk  # Use global SDK instance
        
        # Make the service call
        if method == HTTPMethod.GET:
            response = await service_sdk.get_from_service(
                service_name=service_name,
                path=path,
                response_model=response_model,
                timeout=config.timeout
            )
        elif method == HTTPMethod.POST:
            response = await service_sdk.post_to_service(
                service_name=service_name,
                path=path,
                data=request_data,
                response_model=response_model,
                timeout=config.timeout
            )
        elif method in [HTTPMethod.PUT, HTTPMethod.PATCH, HTTPMethod.DELETE]:
            response = await service_sdk.call_service(
                service_name=service_name,
                method=method.value,
                path=path,
                data=request_data,
                response_model=response_model,
                timeout=config.timeout
            )
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        # Wrap in result
        return ServiceCallResult[T](
            success=True,
            data=response,
            service_name=service_name,
            endpoint=path
        )
        
    except ValidationError as e:
        # Handle Pydantic validation errors
        validation_errors = {}
        for error in e.errors():
            field = '.'.join(str(loc) for loc in error['loc'])
            if field not in validation_errors:
                validation_errors[field] = []
            validation_errors[field].append(error['msg'])
        
        raise ServiceValidationError(
            f"Validation failed for {service_name}",
            service_name=service_name,
            validation_errors=validation_errors
        )
    
    except Exception as e:
        # Handle other errors
        return ServiceCallResult[T](
            success=False,
            error=str(e),
            service_name=service_name,
            endpoint=path
        ) 