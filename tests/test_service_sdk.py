"""Tests for the MSFW Service Communication SDK."""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from typing import Optional

from pydantic import BaseModel

from msfw import (
    ServiceSDK, ServiceClient, ServiceRegistry, ServiceInstance, ServiceEndpoint,
    HTTPMethod, ServiceCallResult, TypedServiceError, ServiceValidationError,
    service_call, retry_on_failure, circuit_breaker, service_interface
)
from msfw.core.service_client import ServiceClientError
from msfw.core.typed_client import TypedServiceClient

# Configure pytest for async tests - only apply to async test classes


# Test models
class User(BaseModel):
    id: int
    name: str
    email: str


class CreateUserRequest(BaseModel):
    name: str
    email: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    created_at: str


@pytest.fixture
def mock_registry():
    """Mock service registry."""
    registry = Mock(spec=ServiceRegistry)
    registry.register_service = AsyncMock()
    registry.deregister_service = AsyncMock()
    registry.discover_service = AsyncMock()
    registry.get_service_endpoint = AsyncMock()
    registry.list_services = AsyncMock()
    registry.heartbeat = AsyncMock()
    registry.shutdown = AsyncMock()
    registry.add_callback = Mock()
    return registry


@pytest.fixture
def mock_client():
    """Mock service client."""
    client = Mock(spec=ServiceClient)
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.delete = AsyncMock()
    client.health_check = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_client_factory():
    """Mock service client factory."""
    factory = Mock()
    factory.get_client = Mock()
    factory.close_all = AsyncMock()
    return factory


@pytest.fixture
def service_sdk(mock_registry, mock_client_factory):
    """Service SDK with mocked dependencies."""
    return ServiceSDK(
        registry=mock_registry,
        client_factory=mock_client_factory
    )


@pytest.mark.asyncio
class TestServiceSDK:
    """Test ServiceSDK functionality."""
    
    async def test_register_current_service(self, service_sdk, mock_registry):
        """Test service registration."""
        await service_sdk.register_current_service(
            service_name="test-service",
            version="1.0.0",
            host="localhost",
            port=8001
        )
        
        mock_registry.register_service.assert_called_once()
        call_args = mock_registry.register_service.call_args[0][0]
        assert call_args.name == "test-service"
        assert call_args.version == "1.0.0"
        assert len(call_args.endpoints) == 1
        assert call_args.endpoints[0].host == "localhost"
        assert call_args.endpoints[0].port == 8001
    
    async def test_register_external_service(self, service_sdk, mock_registry):
        """Test external service registration."""
        await service_sdk.register_external_service(
            service_name="external-service",
            host="external.com",
            port=443,
            protocol="https"
        )
        
        mock_registry.register_service.assert_called_once()
        call_args = mock_registry.register_service.call_args[0][0]
        assert call_args.name == "external-service"
        assert call_args.endpoints[0].protocol == "https"
    
    async def test_discover_services(self, service_sdk, mock_registry):
        """Test service discovery."""
        mock_instance = Mock(spec=ServiceInstance)
        mock_registry.discover_service.return_value = [mock_instance]
        
        services = await service_sdk.discover_services("test-service")
        
        assert len(services) == 1
        assert services[0] == mock_instance
        mock_registry.discover_service.assert_called_once_with("test-service", version=None)
    
    async def test_get_service_endpoint(self, service_sdk, mock_registry):
        """Test getting service endpoint."""
        mock_endpoint = Mock(spec=ServiceEndpoint)
        mock_endpoint.url = "http://localhost:8001"
        mock_registry.get_service_endpoint.return_value = mock_endpoint
        
        endpoint_url = await service_sdk.get_service_endpoint("test-service")
        
        assert endpoint_url == "http://localhost:8001"
        mock_registry.get_service_endpoint.assert_called_once_with("test-service", version=None)
    
    async def test_get_client(self, service_sdk, mock_client_factory, mock_client):
        """Test getting service client."""
        mock_client_factory.get_client.return_value = mock_client
        
        client = service_sdk.get_client("test-service")
        
        assert client == mock_client
        mock_client_factory.get_client.assert_called_once()
    
    async def test_call_service_get(self, service_sdk):
        """Test high-level service call (GET)."""
        with patch.object(service_sdk, 'service_client') as mock_context:
            mock_client = AsyncMock()
            mock_client.get.return_value = {"id": 1, "name": "test"}
            mock_context.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_context.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await service_sdk.call_service(
                service_name="test-service",
                method="GET",
                path="/users/1"
            )
            
            assert result == {"id": 1, "name": "test"}
            mock_client.get.assert_called_once_with("/users/1", response_model=None)
    
    async def test_call_service_post(self, service_sdk):
        """Test high-level service call (POST)."""
        with patch.object(service_sdk, 'service_client') as mock_context:
            mock_client = AsyncMock()
            mock_client.post.return_value = {"id": 2, "name": "created"}
            mock_context.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_context.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await service_sdk.call_service(
                service_name="test-service",
                method="POST",
                path="/users",
                data={"name": "test", "email": "test@example.com"}
            )
            
            assert result == {"id": 2, "name": "created"}
            mock_client.post.assert_called_once()
    
    async def test_check_service_health(self, service_sdk):
        """Test service health check."""
        with patch.object(service_sdk, 'service_client') as mock_context:
            mock_client = AsyncMock()
            mock_client.health_check.return_value = True
            mock_context.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_context.return_value.__aexit__ = AsyncMock(return_value=None)
            
            is_healthy = await service_sdk.check_service_health("test-service")
            
            assert is_healthy is True
            mock_client.health_check.assert_called_once()
    
    async def test_check_multiple_services(self, service_sdk):
        """Test batch health checking."""
        with patch.object(service_sdk, 'check_service_health') as mock_health:
            mock_health.side_effect = [True, False, True]
            
            results = await service_sdk.check_multiple_services(
                ["service1", "service2", "service3"]
            )
            
            assert results == {
                "service1": True,
                "service2": False,
                "service3": True
            }
    
    async def test_call_multiple_services(self, service_sdk):
        """Test batch service calls."""
        with patch.object(service_sdk, 'call_service') as mock_call:
            mock_call.side_effect = [
                {"result": "call1"},
                {"result": "call2"},
                Exception("call3 failed")
            ]
            
            calls = [
                {"service_name": "service1", "path": "/endpoint1"},
                {"service_name": "service2", "path": "/endpoint2"},
                {"service_name": "service3", "path": "/endpoint3"}
            ]
            
            results = await service_sdk.call_multiple_services(calls)
            
            assert len(results) == 3
            assert results[0] == {"result": "call1"}
            assert results[1] == {"result": "call2"}
            assert isinstance(results[2], Exception)
    
    async def test_shutdown(self, service_sdk, mock_registry, mock_client_factory):
        """Test SDK shutdown."""
        service_sdk._current_service = Mock()
        
        await service_sdk.shutdown()
        
        mock_registry.deregister_service.assert_called_once()
        mock_client_factory.close_all.assert_called_once()
        mock_registry.shutdown.assert_called_once()


@pytest.mark.asyncio
class TestServiceCallDecorator:
    """Test service_call decorator."""
    
    async def test_service_call_decorator_get(self):
        """Test service_call decorator for GET request."""
        with patch('msfw.decorators.service._make_typed_service_call') as mock_call:
            mock_result = ServiceCallResult(
                success=True,
                data=User(id=1, name="Test", email="test@example.com"),
                service_name="user-service"
            )
            mock_call.return_value = mock_result
            
            @service_call("user-service", HTTPMethod.GET, "/users/{user_id}")
            async def get_user(user_id: int) -> User:
                pass
            
            result = await get_user(123)
            
            assert isinstance(result, User)
            assert result.id == 1
            mock_call.assert_called_once()
            args = mock_call.call_args[1]
            assert args['service_name'] == "user-service"
            assert args['method'] == HTTPMethod.GET
            assert args['path'] == "/users/123"
    
    async def test_service_call_decorator_post(self):
        """Test service_call decorator for POST request."""
        with patch('msfw.decorators.service._make_typed_service_call') as mock_call:
            mock_result = ServiceCallResult(
                success=True,
                data=User(id=2, name="Created", email="created@example.com"),
                service_name="user-service"
            )
            mock_call.return_value = mock_result
            
            @service_call("user-service", HTTPMethod.POST, "/users")
            async def create_user(user_data: CreateUserRequest) -> User:
                pass
            
            request_data = CreateUserRequest(name="Test", email="test@example.com")
            result = await create_user(request_data)
            
            assert isinstance(result, User)
            assert result.id == 2
            mock_call.assert_called_once()
            args = mock_call.call_args[1]
            assert args['request_data'] == request_data.model_dump()
    
    async def test_service_call_error_handling(self):
        """Test service_call decorator error handling."""
        with patch('msfw.decorators.service._make_typed_service_call') as mock_call:
            mock_call.side_effect = Exception("Service unavailable")
            
            @service_call("user-service", HTTPMethod.GET, "/users/{user_id}")
            async def get_user(user_id: int) -> User:
                pass
            
            with pytest.raises(TypedServiceError) as exc_info:
                await get_user(123)
            
            assert "Service call to user-service failed" in str(exc_info.value)


@pytest.mark.asyncio
class TestRetryDecorator:
    """Test retry_on_failure decorator."""
    
    async def test_retry_success_on_first_attempt(self):
        """Test retry decorator with success on first attempt."""
        call_count = 0
        
        @retry_on_failure(max_attempts=3, delay=0.1)
        async def test_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await test_function()
        
        assert result == "success"
        assert call_count == 1
    
    async def test_retry_success_after_failures(self):
        """Test retry decorator with success after failures."""
        call_count = 0
        
        @retry_on_failure(max_attempts=3, delay=0.1)
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Attempt {call_count} failed")
            return "success"
        
        result = await test_function()
        
        assert result == "success"
        assert call_count == 3
    
    async def test_retry_all_attempts_fail(self):
        """Test retry decorator when all attempts fail."""
        call_count = 0
        
        @retry_on_failure(max_attempts=3, delay=0.1)
        async def test_function():
            nonlocal call_count
            call_count += 1
            raise Exception(f"Attempt {call_count} failed")
        
        with pytest.raises(Exception) as exc_info:
            await test_function()
        
        assert "Attempt 3 failed" in str(exc_info.value)
        assert call_count == 3


@pytest.mark.asyncio
class TestCircuitBreakerDecorator:
    """Test circuit_breaker decorator."""
    
    async def test_circuit_breaker_normal_operation(self):
        """Test circuit breaker in normal operation."""
        @circuit_breaker(failure_threshold=3, recovery_timeout=1.0)
        async def test_function():
            return "success"
        
        result = await test_function()
        assert result == "success"
    
    async def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures."""
        call_count = 0
        
        @circuit_breaker(failure_threshold=2, recovery_timeout=1.0)
        async def test_function():
            nonlocal call_count
            call_count += 1
            raise Exception(f"Failure {call_count}")
        
        # First two calls should fail normally
        with pytest.raises(Exception):
            await test_function()
        
        with pytest.raises(Exception):
            await test_function()
        
        # Third call should fail with circuit breaker open
        with pytest.raises(TypedServiceError) as exc_info:
            await test_function()
        
        assert "Circuit breaker is open" in str(exc_info.value)
        assert call_count == 2  # Function not called when circuit is open


class TestServiceInterface:
    """Test service_interface decorator."""
    
    def test_service_interface_decorator(self):
        """Test service_interface class decorator."""
        @service_interface("user-service", "/api/v1")
        class UserService:
            pass
        
        assert UserService._service_name == "user-service"
        assert UserService._base_path == "/api/v1"
        assert hasattr(UserService, '_sdk')


class TestServiceCallResult:
    """Test ServiceCallResult functionality."""
    
    def test_service_call_result_success(self):
        """Test successful ServiceCallResult."""
        user = User(id=1, name="Test", email="test@example.com")
        result = ServiceCallResult(
            success=True,
            data=user,
            service_name="user-service"
        )
        
        assert result.is_success
        assert result.unwrap() == user
    
    def test_service_call_result_failure(self):
        """Test failed ServiceCallResult."""
        result = ServiceCallResult(
            success=False,
            error="Service unavailable",
            service_name="user-service"
        )
        
        assert not result.is_success
        
        with pytest.raises(ValueError) as exc_info:
            result.unwrap()
        
        assert "Service call failed" in str(exc_info.value)
    
    def test_service_call_result_no_data(self):
        """Test ServiceCallResult with success but no data."""
        result = ServiceCallResult(
            success=True,
            data=None,
            service_name="user-service"
        )
        
        assert result.is_success
        
        with pytest.raises(ValueError) as exc_info:
            result.unwrap()
        
        assert "succeeded but returned no data" in str(exc_info.value)


@pytest.mark.asyncio
class TestTypedServiceClient:
    """Test TypedServiceClient functionality."""
    
    async def test_typed_client_get_request(self, mock_client):
        """Test typed client GET request."""
        mock_client.get.return_value = {
            "id": 1, 
            "name": "Test", 
            "email": "test@example.com"
        }
        
        typed_client = TypedServiceClient(
            service_name="user-service",
            client=mock_client,
            response_model=User
        )
        
        result = await typed_client.get("/users/1")
        
        assert result.is_success
        assert isinstance(result.data, User)  # TypedServiceClient validates and converts to User model
        mock_client.get.assert_called_once_with(
            path="/users/1",
            params=None,
            response_model=User
        )
    
    async def test_typed_client_post_request(self, mock_client):
        """Test typed client POST request."""
        request_data = CreateUserRequest(name="Test", email="test@example.com")
        mock_client.post.return_value = {
            "id": 1,
            "name": "Test",
            "email": "test@example.com",
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        typed_client = TypedServiceClient(
            service_name="user-service",
            client=mock_client,
            request_model=CreateUserRequest,
            response_model=UserResponse
        )
        
        result = await typed_client.post("/users", request_data=request_data)
        
        assert result.is_success
        mock_client.post.assert_called_once_with(
            path="/users",
            json_data=request_data.model_dump(),
            response_model=UserResponse
        )
    
    async def test_typed_client_validation_error(self, mock_client):
        """Test typed client with invalid request data."""
        invalid_data = "not a model instance"
        
        typed_client = TypedServiceClient(
            service_name="user-service",
            client=mock_client,
            request_model=CreateUserRequest
        )
        
        with pytest.raises(TypedServiceError) as exc_info:
            await typed_client.post("/users", request_data=invalid_data)
        
        assert "Request data must be of type" in str(exc_info.value)
    
    async def test_typed_client_service_error(self, mock_client):
        """Test typed client handling service errors."""
        mock_client.get.side_effect = ServiceClientError("Service unavailable")
        
        typed_client = TypedServiceClient(
            service_name="user-service",
            client=mock_client
        )
        
        result = await typed_client.get("/users/1")
        
        assert not result.is_success
        assert "Service unavailable" in result.error


@pytest.mark.asyncio  
class TestIntegration:
    """Integration tests for the service communication SDK."""
    
    async def test_end_to_end_service_communication(self):
        """Test end-to-end service communication flow."""
        # This would be a more complex integration test
        # For now, we'll test the basic flow with mocks
        
        sdk = ServiceSDK()
        
        # Register a service
        await sdk.register_current_service(
            service_name="test-service",
            host="localhost",
            port=8001
        )
        
        # The service should be registered
        assert sdk._current_service is not None
        assert sdk._current_service.name == "test-service"


if __name__ == "__main__":
    pytest.main([__file__]) 