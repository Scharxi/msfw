"""Type-safe service client for MSFW."""

from typing import TypeVar, Generic, Type, Optional, Dict, Any, Union
import logging

from pydantic import BaseModel, ValidationError

from msfw.core.types import (
    HTTPMethod, ServiceCallResult, ServiceCallConfig,
    TypedServiceError, ServiceValidationError, RequestT, ResponseT
)
from msfw.core.service_client import ServiceClient, ServiceClientError


T = TypeVar('T', bound=BaseModel)
RequestModel = TypeVar('RequestModel', bound=BaseModel)
ResponseModel = TypeVar('ResponseModel', bound=BaseModel)

logger = logging.getLogger(__name__)


class TypedServiceClient(Generic[RequestModel, ResponseModel]):
    """Type-safe wrapper around ServiceClient."""
    
    def __init__(
        self,
        service_name: str,
        client: ServiceClient,
        request_model: Optional[Type[RequestModel]] = None,
        response_model: Optional[Type[ResponseModel]] = None
    ):
        self.service_name = service_name
        self.client = client
        self.request_model = request_model
        self.response_model = response_model
        self.logger = logging.getLogger(f"{__name__}.{service_name}")
    
    async def get(
        self,
        path: str = "",
        params: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[T]] = None
    ) -> ServiceCallResult[Union[T, ResponseModel]]:
        """Type-safe GET request."""
        return await self._make_request(
            method=HTTPMethod.GET,
            path=path,
            params=params,
            response_model=response_model
        )
    
    async def post(
        self,
        path: str = "",
        request_data: Optional[RequestModel] = None,
        json_data: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[T]] = None
    ) -> ServiceCallResult[Union[T, ResponseModel]]:
        """Type-safe POST request."""
        # Validate and serialize request data
        data = None
        if request_data:
            if self.request_model and not isinstance(request_data, self.request_model):
                raise TypedServiceError(
                    f"Request data must be of type {self.request_model.__name__}",
                    service_name=self.service_name
                )
            data = request_data.model_dump()
        elif json_data:
            data = json_data
        
        return await self._make_request(
            method=HTTPMethod.POST,
            path=path,
            json_data=data,
            response_model=response_model
        )
    
    async def put(
        self,
        path: str = "",
        request_data: Optional[RequestModel] = None,
        json_data: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[T]] = None
    ) -> ServiceCallResult[Union[T, ResponseModel]]:
        """Type-safe PUT request."""
        data = None
        if request_data:
            if self.request_model and not isinstance(request_data, self.request_model):
                raise TypedServiceError(
                    f"Request data must be of type {self.request_model.__name__}",
                    service_name=self.service_name
                )
            data = request_data.model_dump()
        elif json_data:
            data = json_data
        
        return await self._make_request(
            method=HTTPMethod.PUT,
            path=path,
            json_data=data,
            response_model=response_model
        )
    
    async def delete(
        self,
        path: str = "",
        response_model: Optional[Type[T]] = None
    ) -> ServiceCallResult[Union[T, ResponseModel]]:
        """Type-safe DELETE request."""
        return await self._make_request(
            method=HTTPMethod.DELETE,
            path=path,
            response_model=response_model
        )
    
    async def _make_request(
        self,
        method: HTTPMethod,
        path: str = "",
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[T]] = None
    ) -> ServiceCallResult[Union[T, ResponseModel]]:
        """Internal method to make typed requests."""
        
        # Determine response model
        expected_response_model = response_model or self.response_model
        
        try:
            # Make the actual request
            if method == HTTPMethod.GET:
                response = await self.client.get(
                    path=path,
                    params=params,
                    response_model=expected_response_model
                )
            elif method == HTTPMethod.POST:
                response = await self.client.post(
                    path=path,
                    json_data=json_data,
                    response_model=expected_response_model
                )
            elif method == HTTPMethod.PUT:
                response = await self.client.put(
                    path=path,
                    json_data=json_data,
                    response_model=expected_response_model
                )
            elif method == HTTPMethod.DELETE:
                response = await self.client.delete(
                    path=path,
                    response_model=expected_response_model
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Validate response type if model is specified
            if expected_response_model and response:
                try:
                    if isinstance(response, dict):
                        validated_response = expected_response_model(**response)
                    elif isinstance(response, expected_response_model):
                        validated_response = response
                    else:
                        # Try to convert
                        validated_response = expected_response_model.model_validate(response)
                    
                    return ServiceCallResult[Union[T, ResponseModel]](
                        success=True,
                        data=validated_response,
                        service_name=self.service_name,
                        endpoint=path
                    )
                    
                except ValidationError as e:
                    self.logger.error(f"Response validation failed: {e}")
                    
                    # Create detailed validation error
                    validation_errors = {}
                    for error in e.errors():
                        field = '.'.join(str(loc) for loc in error['loc'])
                        if field not in validation_errors:
                            validation_errors[field] = []
                        validation_errors[field].append(error['msg'])
                    
                    raise ServiceValidationError(
                        f"Response validation failed for {self.service_name}",
                        service_name=self.service_name,
                        validation_errors=validation_errors
                    )
            
            # Return unvalidated response
            return ServiceCallResult[Union[T, ResponseModel]](
                success=True,
                data=response,
                service_name=self.service_name,
                endpoint=path
            )
            
        except ServiceClientError as e:
            self.logger.error(f"Service client error: {e}")
            return ServiceCallResult[Union[T, ResponseModel]](
                success=False,
                error=str(e),
                service_name=self.service_name,
                endpoint=path
            )
        
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise TypedServiceError(
                f"Request to {self.service_name} failed: {str(e)}",
                service_name=self.service_name
            ) from e
    
    async def health_check(self) -> bool:
        """Check service health."""
        try:
            result = await self.get("/health")
            return result.is_success
        except Exception:
            return False
    
    async def close(self) -> None:
        """Close the underlying client."""
        await self.client.close()


class TypedServiceClientFactory:
    """Factory for creating typed service clients."""
    
    def __init__(self, sdk):
        self.sdk = sdk
        self._typed_clients: Dict[str, TypedServiceClient] = {}
    
    def create_client(
        self,
        service_name: str,
        request_model: Optional[Type[RequestModel]] = None,
        response_model: Optional[Type[ResponseModel]] = None,
        **client_kwargs
    ) -> TypedServiceClient[RequestModel, ResponseModel]:
        """Create a typed service client."""
        
        # Get base service client
        base_client = self.sdk.get_client(service_name, **client_kwargs)
        
        # Create typed wrapper
        typed_client = TypedServiceClient(
            service_name=service_name,
            client=base_client,
            request_model=request_model,
            response_model=response_model
        )
        
        return typed_client
    
    def get_client(
        self,
        service_name: str,
        request_model: Optional[Type[RequestModel]] = None,
        response_model: Optional[Type[ResponseModel]] = None,
        **client_kwargs
    ) -> TypedServiceClient[RequestModel, ResponseModel]:
        """Get or create a typed service client."""
        
        client_key = f"{service_name}:{request_model}:{response_model}"
        
        if client_key not in self._typed_clients:
            self._typed_clients[client_key] = self.create_client(
                service_name=service_name,
                request_model=request_model,
                response_model=response_model,
                **client_kwargs
            )
        
        return self._typed_clients[client_key]
    
    async def close_all(self) -> None:
        """Close all typed clients."""
        for client in self._typed_clients.values():
            await client.close()
        self._typed_clients.clear()


# Type-safe service interface base classes
class BaseServiceInterface(Generic[RequestModel, ResponseModel]):
    """Base class for type-safe service interfaces."""
    
    def __init__(
        self,
        client: TypedServiceClient[RequestModel, ResponseModel],
        base_path: str = ""
    ):
        self.client = client
        self.base_path = base_path.rstrip('/')
    
    def _build_path(self, path: str) -> str:
        """Build full path with base path."""
        if not path.startswith('/'):
            path = f'/{path}'
        return f"{self.base_path}{path}"
    
    async def health_check(self) -> bool:
        """Check service health."""
        return await self.client.health_check()


# Specialized service interfaces for common patterns
class CRUDServiceInterface(BaseServiceInterface[RequestModel, ResponseModel]):
    """CRUD service interface with type safety."""
    
    async def create(self, data: RequestModel) -> ServiceCallResult[ResponseModel]:
        """Create a new resource."""
        return await self.client.post(
            path=self._build_path(""),
            request_data=data
        )
    
    async def get(self, resource_id: Union[int, str]) -> ServiceCallResult[ResponseModel]:
        """Get a resource by ID."""
        return await self.client.get(
            path=self._build_path(f"/{resource_id}")
        )
    
    async def update(
        self, 
        resource_id: Union[int, str], 
        data: RequestModel
    ) -> ServiceCallResult[ResponseModel]:
        """Update a resource."""
        return await self.client.put(
            path=self._build_path(f"/{resource_id}"),
            request_data=data
        )
    
    async def delete(self, resource_id: Union[int, str]) -> ServiceCallResult[ResponseModel]:
        """Delete a resource."""
        return await self.client.delete(
            path=self._build_path(f"/{resource_id}")
        )
    
    async def list(
        self, 
        params: Optional[Dict[str, Any]] = None
    ) -> ServiceCallResult[ResponseModel]:
        """List resources."""
        return await self.client.get(
            path=self._build_path(""),
            params=params
        ) 