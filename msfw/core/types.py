"""Type definitions and protocols for MSFW service communication."""

from typing import (
    TypeVar, Generic, Protocol, runtime_checkable,
    Dict, Any, Optional, Union, List, Callable, Awaitable,
    Type, ClassVar
)
from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel


# Generic type variables
T = TypeVar('T')
ResponseT = TypeVar('ResponseT', bound=BaseModel)
RequestT = TypeVar('RequestT', bound=BaseModel)


class HTTPMethod(str, Enum):
    """HTTP methods enumeration."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ServiceCallResult(BaseModel, Generic[T]):
    """Typed result wrapper for service calls."""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    service_name: str
    endpoint: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        """Check if the call was successful."""
        return self.success and self.error is None
    
    def unwrap(self) -> T:
        """Unwrap the result data or raise an exception."""
        if not self.is_success:
            raise ValueError(f"Service call failed: {self.error}")
        if self.data is None:
            raise ValueError("Service call succeeded but returned no data")
        return self.data


@runtime_checkable
class ServiceEndpointProtocol(Protocol):
    """Protocol for service endpoints."""
    host: str
    port: int
    protocol: str
    path: str
    
    @property
    def url(self) -> str:
        """Get the full URL for this endpoint."""
        ...


@runtime_checkable
class ServiceInstanceProtocol(Protocol):
    """Protocol for service instances."""
    name: str
    version: str
    endpoints: List[ServiceEndpointProtocol]
    metadata: Dict[str, Any]
    status: str


@runtime_checkable
class ServiceRegistryProtocol(Protocol):
    """Protocol for service registry."""
    
    async def register_service(self, service: ServiceInstanceProtocol) -> None:
        """Register a service instance."""
        ...
    
    async def deregister_service(self, service_name: str) -> None:
        """Deregister a service."""
        ...
    
    async def discover_service(self, service_name: str) -> List[ServiceInstanceProtocol]:
        """Discover service instances."""
        ...
    
    async def get_service_endpoint(self, service_name: str) -> Optional[ServiceEndpointProtocol]:
        """Get a service endpoint."""
        ...


@runtime_checkable
class ServiceClientProtocol(Protocol):
    """Protocol for service clients."""
    
    async def get(
        self, 
        path: str = "",
        params: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[T]] = None
    ) -> Any:
        """Perform GET request."""
        ...
    
    async def post(
        self,
        path: str = "",
        json_data: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[T]] = None
    ) -> Any:
        """Perform POST request."""
        ...


class ServiceCallConfig(BaseModel):
    """Configuration for service calls."""
    timeout: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    circuit_breaker_enabled: bool = True
    failure_threshold: int = 5
    success_threshold: int = 2
    circuit_timeout: float = 60.0


# Callback type definitions
ServiceEventCallback = Callable[[ServiceInstanceProtocol], Union[None, Awaitable[None]]]
ServiceHealthCallback = Callable[[str, bool], Union[None, Awaitable[None]]]
ServiceErrorCallback = Callable[[str, Exception], Union[None, Awaitable[None]]]


class ServiceMethodDefinition(BaseModel, Generic[RequestT, ResponseT]):
    """Type-safe service method definition."""
    service_name: str
    method: HTTPMethod
    path: str
    request_model: Optional[Type[RequestT]] = None
    response_model: Optional[Type[ResponseT]] = None
    config: ServiceCallConfig = ServiceCallConfig()
    
    async def call(
        self, 
        client: ServiceClientProtocol,
        request_data: Optional[RequestT] = None,
        **kwargs
    ) -> ServiceCallResult[ResponseT]:
        """Execute the service call."""
        # This will be implemented by the actual service client
        raise NotImplementedError("Must be implemented by service client")


class TypedServiceInterface(ABC, Generic[RequestT, ResponseT]):
    """Base class for typed service interfaces."""
    
    service_name: ClassVar[str]
    base_path: ClassVar[str] = ""
    
    def __init__(self, client: ServiceClientProtocol):
        self.client = client
    
    @abstractmethod
    async def call(self, request: RequestT) -> ServiceCallResult[ResponseT]:
        """Make a typed service call."""
        pass


# Exception types with better type information
class TypedServiceError(Exception, Generic[T]):
    """Typed service error."""
    
    def __init__(
        self, 
        message: str, 
        service_name: str,
        response_data: Optional[T] = None,
        status_code: Optional[int] = None
    ):
        super().__init__(message)
        self.service_name = service_name
        self.response_data = response_data
        self.status_code = status_code


class ServiceValidationError(TypedServiceError[Dict[str, Any]]):
    """Service validation error with detailed field information."""
    
    def __init__(
        self, 
        message: str,
        service_name: str, 
        validation_errors: Dict[str, List[str]],
        status_code: int = 422
    ):
        super().__init__(message, service_name, validation_errors, status_code)
        self.validation_errors = validation_errors


# Type aliases for common patterns
ServiceCall = Callable[..., Awaitable[ServiceCallResult[T]]]
ServiceMethod = ServiceMethodDefinition[RequestT, ResponseT]
ServiceInterface = TypedServiceInterface[RequestT, ResponseT] 