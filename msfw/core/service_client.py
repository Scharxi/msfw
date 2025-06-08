"""HTTP Client for inter-service communication with resilience patterns."""

import asyncio
import time
import json
from typing import Dict, Any, Optional, Union, List, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
import logging

import aiohttp
from pydantic import BaseModel, ValidationError

from msfw.core.service_registry import ServiceRegistry, ServiceEndpoint, service_registry


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, requests rejected
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5          # Failures before opening
    success_threshold: int = 2          # Successes to close from half-open
    timeout: float = 60.0              # Timeout before trying half-open (seconds)
    retry_attempts: int = 3            # Number of retry attempts
    retry_delay: float = 1.0           # Initial retry delay (seconds)
    retry_backoff: float = 2.0         # Backoff multiplier
    request_timeout: float = 30.0      # Request timeout (seconds)


@dataclass
class CircuitBreakerState:
    """Circuit breaker state tracking."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0
    last_request_time: float = 0


class ServiceClientError(Exception):
    """Base exception for service client errors."""
    pass


class ServiceUnavailableError(ServiceClientError):
    """Service is unavailable."""
    pass


class CircuitOpenError(ServiceClientError):
    """Circuit breaker is open."""
    pass


class ServiceClient:
    """HTTP client for inter-service communication with resilience patterns."""
    
    def __init__(
        self,
        service_name: str,
        registry: Optional[ServiceRegistry] = None,
        circuit_config: Optional[CircuitBreakerConfig] = None,
        default_timeout: float = 30.0,
        default_headers: Optional[Dict[str, str]] = None
    ):
        self.service_name = service_name
        self.registry = registry or service_registry
        self.circuit_config = circuit_config or CircuitBreakerConfig()
        self.default_timeout = default_timeout
        self.default_headers = default_headers or {}
        
        # Circuit breaker state per endpoint
        self._circuit_states: Dict[str, CircuitBreakerState] = {}
        
        # Session management
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_created_at: float = 0
        self._session_ttl: float = 300  # 5 minutes
        
        self.logger = logging.getLogger(f"{__name__}.{service_name}")
    
    async def get(
        self, 
        path: str = "",
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        response_model: Optional[Type[BaseModel]] = None
    ) -> Any:
        """Perform GET request to service."""
        return await self._request(
            "GET", path, params=params, headers=headers, 
            timeout=timeout, response_model=response_model
        )
    
    async def post(
        self,
        path: str = "",
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        response_model: Optional[Type[BaseModel]] = None
    ) -> Any:
        """Perform POST request to service."""
        return await self._request(
            "POST", path, json_data=json_data, data=data,
            headers=headers, timeout=timeout, response_model=response_model
        )
    
    async def put(
        self,
        path: str = "",
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        response_model: Optional[Type[BaseModel]] = None
    ) -> Any:
        """Perform PUT request to service."""
        return await self._request(
            "PUT", path, json_data=json_data, data=data,
            headers=headers, timeout=timeout, response_model=response_model
        )
    
    async def delete(
        self,
        path: str = "",
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        response_model: Optional[Type[BaseModel]] = None
    ) -> Any:
        """Perform DELETE request to service."""
        return await self._request(
            "DELETE", path, headers=headers, 
            timeout=timeout, response_model=response_model
        )
    
    async def _request(
        self,
        method: str,
        path: str = "",
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        response_model: Optional[Type[BaseModel]] = None
    ) -> Any:
        """Perform HTTP request with circuit breaker and retry logic."""
        
        # Get service endpoint
        endpoint = await self._get_endpoint()
        if not endpoint:
            raise ServiceUnavailableError(f"No healthy instances of service '{self.service_name}' found")
        
        # Check circuit breaker
        circuit_key = f"{endpoint.host}:{endpoint.port}"
        if not self._can_execute(circuit_key):
            raise CircuitOpenError(f"Circuit breaker is open for {self.service_name}")
        
        # Prepare request
        url = self._build_url(endpoint, path)
        request_headers = {**self.default_headers, **(headers or {})}
        request_timeout = timeout or self.default_timeout
        
        # Execute with retry logic
        last_exception = None
        for attempt in range(self.circuit_config.retry_attempts):
            try:
                session = await self._get_session()
                
                async with session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    data=data,
                    headers=request_headers,
                    timeout=aiohttp.ClientTimeout(total=request_timeout)
                ) as response:
                    
                    # Handle response
                    if response.status >= 200 and response.status < 300:
                        self._record_success(circuit_key)
                        return await self._parse_response(response, response_model)
                    elif response.status >= 500:
                        # Server error - count as failure for circuit breaker
                        self._record_failure(circuit_key)
                        raise ServiceClientError(f"Server error: {response.status}")
                    else:
                        # Client error - don't count as circuit breaker failure
                        raise ServiceClientError(f"Client error: {response.status}")
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                self._record_failure(circuit_key)
                
                # Retry with backoff (except for last attempt)
                if attempt < self.circuit_config.retry_attempts - 1:
                    delay = self.circuit_config.retry_delay * (
                        self.circuit_config.retry_backoff ** attempt
                    )
                    await asyncio.sleep(delay)
                    self.logger.warning(
                        f"Request failed (attempt {attempt + 1}), retrying in {delay}s: {e}"
                    )
        
        # All retries failed
        if last_exception:
            raise ServiceClientError(f"Request failed after {self.circuit_config.retry_attempts} attempts") from last_exception
        else:
            raise ServiceClientError("Request failed for unknown reason")
    
    async def _get_endpoint(self) -> Optional[ServiceEndpoint]:
        """Get a healthy service endpoint."""
        return await self.registry.get_service_endpoint(self.service_name)
    
    def _build_url(self, endpoint: ServiceEndpoint, path: str) -> str:
        """Build full URL for request."""
        base_url = endpoint.url.rstrip("/")
        if path and not path.startswith("/"):
            path = f"/{path}"
        return f"{base_url}{path}"
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        now = time.time()
        
        # Create new session if needed
        if (not self._session or 
            self._session.closed or 
            now - self._session_created_at > self._session_ttl):
            
            if self._session and not self._session.closed:
                await self._session.close()
            
            self._session = aiohttp.ClientSession()
            self._session_created_at = now
        
        return self._session
    
    async def _parse_response(
        self, 
        response: aiohttp.ClientResponse, 
        response_model: Optional[Type[BaseModel]] = None
    ) -> Any:
        """Parse HTTP response."""
        if response.content_type == "application/json":
            data = await response.json()
            
            if response_model:
                try:
                    return response_model(**data)
                except ValidationError as e:
                    self.logger.warning(f"Response validation failed: {e}")
                    return data
            else:
                return data
        else:
            return await response.text()
    
    def _can_execute(self, circuit_key: str) -> bool:
        """Check if request can be executed based on circuit breaker state."""
        if circuit_key not in self._circuit_states:
            self._circuit_states[circuit_key] = CircuitBreakerState()
        
        state = self._circuit_states[circuit_key]
        now = time.time()
        
        if state.state == CircuitState.CLOSED:
            return True
        elif state.state == CircuitState.OPEN:
            # Check if timeout has passed
            if now - state.last_failure_time >= self.circuit_config.timeout:
                state.state = CircuitState.HALF_OPEN
                state.success_count = 0
                return True
            return False
        elif state.state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    def _record_success(self, circuit_key: str) -> None:
        """Record successful request."""
        if circuit_key not in self._circuit_states:
            self._circuit_states[circuit_key] = CircuitBreakerState()
        
        state = self._circuit_states[circuit_key]
        state.last_request_time = time.time()
        
        if state.state == CircuitState.HALF_OPEN:
            state.success_count += 1
            if state.success_count >= self.circuit_config.success_threshold:
                state.state = CircuitState.CLOSED
                state.failure_count = 0
                state.success_count = 0
        elif state.state == CircuitState.CLOSED:
            # Reset failure count on success
            state.failure_count = 0
    
    def _record_failure(self, circuit_key: str) -> None:
        """Record failed request."""
        if circuit_key not in self._circuit_states:
            self._circuit_states[circuit_key] = CircuitBreakerState()
        
        state = self._circuit_states[circuit_key]
        state.failure_count += 1
        state.last_failure_time = time.time()
        state.last_request_time = time.time()
        
        if (state.state == CircuitState.CLOSED and 
            state.failure_count >= self.circuit_config.failure_threshold):
            state.state = CircuitState.OPEN
            self.logger.warning(f"Circuit breaker opened for {self.service_name} ({circuit_key})")
        elif state.state == CircuitState.HALF_OPEN:
            state.state = CircuitState.OPEN
            state.success_count = 0
            self.logger.warning(f"Circuit breaker reopened for {self.service_name} ({circuit_key})")
    
    def get_circuit_state(self, endpoint: Optional[str] = None) -> Dict[str, CircuitBreakerState]:
        """Get circuit breaker states."""
        if endpoint:
            return {endpoint: self._circuit_states.get(endpoint, CircuitBreakerState())}
        return self._circuit_states.copy()
    
    async def health_check(self) -> bool:
        """Check if service is healthy."""
        try:
            await self.get("/health", timeout=5.0)
            return True
        except Exception:
            return False
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()


class ServiceClientFactory:
    """Factory for creating service clients."""
    
    def __init__(self, registry: Optional[ServiceRegistry] = None):
        self.registry = registry or service_registry
        self._clients: Dict[str, ServiceClient] = {}
    
    def get_client(
        self, 
        service_name: str,
        circuit_config: Optional[CircuitBreakerConfig] = None,
        **client_kwargs
    ) -> ServiceClient:
        """Get or create service client."""
        if service_name not in self._clients:
            self._clients[service_name] = ServiceClient(
                service_name=service_name,
                registry=self.registry,
                circuit_config=circuit_config,
                **client_kwargs
            )
        return self._clients[service_name]
    
    async def close_all(self) -> None:
        """Close all service clients."""
        for client in self._clients.values():
            await client.close()
        self._clients.clear()


# Global service client factory
service_client_factory = ServiceClientFactory() 