"""MSFW Inter-Service Communication SDK."""

import asyncio
from typing import Dict, Any, Optional, Type, List, Callable
from contextlib import asynccontextmanager
import logging

from pydantic import BaseModel

from msfw.core.service_registry import (
    ServiceRegistry, ServiceInstance, ServiceEndpoint, 
    ServiceStatus, service_registry
)
from msfw.core.service_client import (
    ServiceClient, ServiceClientFactory, CircuitBreakerConfig,
    service_client_factory
)
from msfw.core.config import Config


class ServiceSDK:
    """High-level SDK for inter-service communication."""
    
    def __init__(
        self,
        config: Optional[Config] = None,
        registry: Optional[ServiceRegistry] = None,
        client_factory: Optional[ServiceClientFactory] = None
    ):
        self.config = config or Config()
        self.registry = registry or service_registry
        self.client_factory = client_factory or service_client_factory
        self.logger = logging.getLogger(__name__)
        
        # Auto-registration settings
        self._auto_register_enabled = True
        self._current_service: Optional[ServiceInstance] = None
    
    # Service Registration API
    async def register_current_service(
        self,
        service_name: str,
        version: str = "1.0.0",
        host: str = "0.0.0.0",
        port: int = 8000,
        metadata: Optional[Dict[str, Any]] = None,
        health_check_path: str = "/health"
    ) -> None:
        """Register the current service instance."""
        endpoint = ServiceEndpoint(
            host=host,
            port=port,
            protocol="http"
        )
        
        service = ServiceInstance(
            name=service_name,
            version=version,
            endpoints=[endpoint],
            metadata=metadata or {},
            health_check_url=f"http://{host}:{port}{health_check_path}"
        )
        
        await self.registry.register_service(service)
        self._current_service = service
        self.logger.info(f"Registered service: {service_name} v{version} at {host}:{port}")
    
    async def deregister_current_service(self) -> None:
        """Deregister the current service instance."""
        if self._current_service:
            await self.registry.deregister_service(
                self._current_service.name,
                self._current_service.endpoints
            )
            self._current_service = None
    
    async def register_external_service(
        self,
        service_name: str,
        host: str,
        port: int,
        version: str = "1.0.0",
        protocol: str = "http",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register an external service (not managed by MSFW)."""
        endpoint = ServiceEndpoint(
            host=host,
            port=port,
            protocol=protocol
        )
        
        service = ServiceInstance(
            name=service_name,
            version=version,
            endpoints=[endpoint],
            metadata=metadata or {}
        )
        
        await self.registry.register_service(service)
        self.logger.info(f"Registered external service: {service_name} at {host}:{port}")
    
    # Service Discovery API
    async def discover_services(self, service_name: str) -> List[ServiceInstance]:
        """Discover all healthy instances of a service."""
        return await self.registry.discover_service(service_name)
    
    async def get_service_endpoint(self, service_name: str) -> Optional[str]:
        """Get a service endpoint URL."""
        endpoint = await self.registry.get_service_endpoint(service_name)
        return endpoint.url if endpoint else None
    
    async def list_all_services(self) -> Dict[str, List[ServiceInstance]]:
        """List all registered services."""
        return await self.registry.list_services()
    
    # Service Communication API
    def get_client(
        self, 
        service_name: str,
        timeout: float = 30.0,
        retry_attempts: int = 3,
        circuit_breaker: bool = True,
        **kwargs
    ) -> ServiceClient:
        """Get a service client for inter-service communication."""
        circuit_config = None
        if circuit_breaker:
            circuit_config = CircuitBreakerConfig(
                retry_attempts=retry_attempts,
                request_timeout=timeout,
                **kwargs
            )
        
        return self.client_factory.get_client(
            service_name=service_name,
            circuit_config=circuit_config,
            default_timeout=timeout
        )
    
    @asynccontextmanager
    async def service_client(self, service_name: str, **kwargs):
        """Context manager for service client."""
        client = self.get_client(service_name, **kwargs)
        try:
            yield client
        finally:
            await client.close()
    
    # High-level Communication Methods
    async def call_service(
        self,
        service_name: str,
        method: str = "GET",
        path: str = "",
        data: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[BaseModel]] = None,
        timeout: float = 30.0,
        **kwargs
    ) -> Any:
        """Make a simple service call."""
        async with self.service_client(service_name, timeout=timeout, **kwargs) as client:
            if method.upper() == "GET":
                return await client.get(path, response_model=response_model)
            elif method.upper() == "POST":
                return await client.post(path, json_data=data, response_model=response_model)
            elif method.upper() == "PUT":
                return await client.put(path, json_data=data, response_model=response_model)
            elif method.upper() == "DELETE":
                return await client.delete(path, response_model=response_model)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
    
    async def get_from_service(
        self,
        service_name: str,
        path: str = "",
        params: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[BaseModel]] = None,
        **kwargs
    ) -> Any:
        """GET request to service."""
        async with self.service_client(service_name, **kwargs) as client:
            return await client.get(path, params=params, response_model=response_model)
    
    async def post_to_service(
        self,
        service_name: str,
        path: str = "",
        data: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[BaseModel]] = None,
        **kwargs
    ) -> Any:
        """POST request to service."""
        async with self.service_client(service_name, **kwargs) as client:
            return await client.post(path, json_data=data, response_model=response_model)
    
    # Service Health Monitoring
    async def check_service_health(self, service_name: str) -> bool:
        """Check if a service is healthy."""
        try:
            async with self.service_client(service_name, timeout=5.0) as client:
                return await client.health_check()
        except Exception:
            return False
    
    async def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Get detailed service status."""
        services = await self.discover_services(service_name)
        
        if not services:
            return {
                "service": service_name,
                "status": "not_found",
                "instances": 0,
                "healthy_instances": 0
            }
        
        healthy_count = sum(1 for s in services if s.status == ServiceStatus.HEALTHY)
        
        return {
            "service": service_name,
            "status": "healthy" if healthy_count > 0 else "unhealthy",
            "instances": len(services),
            "healthy_instances": healthy_count,
            "endpoints": [
                {
                    "url": ep.url,
                    "status": service.status,
                    "version": service.version
                }
                for service in services
                for ep in service.endpoints
            ]
        }
    
    # Batch Operations
    async def check_multiple_services(self, service_names: List[str]) -> Dict[str, bool]:
        """Check health of multiple services concurrently."""
        tasks = {
            name: self.check_service_health(name)
            for name in service_names
        }
        
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        return {
            name: result if not isinstance(result, Exception) else False
            for name, result in zip(service_names, results)
        }
    
    async def call_multiple_services(
        self,
        calls: List[Dict[str, Any]]
    ) -> List[Any]:
        """Make multiple service calls concurrently.
        
        Args:
            calls: List of call specifications, each containing:
                - service_name: str
                - method: str (optional, default "GET")
                - path: str (optional)
                - data: dict (optional)
                - response_model: Type[BaseModel] (optional)
        """
        tasks = []
        for call_spec in calls:
            task = self.call_service(
                service_name=call_spec["service_name"],
                method=call_spec.get("method", "GET"),
                path=call_spec.get("path", ""),
                data=call_spec.get("data"),
                response_model=call_spec.get("response_model")
            )
            tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    # Event Callbacks
    def on_service_registered(self, callback: Callable[[ServiceInstance], None]) -> None:
        """Register callback for service registration events."""
        self.registry.add_callback("service_registered", callback)
    
    def on_service_deregistered(self, callback: Callable[[ServiceInstance], None]) -> None:
        """Register callback for service deregistration events."""
        self.registry.add_callback("service_deregistered", callback)
    
    def on_service_unhealthy(self, callback: Callable[[ServiceInstance], None]) -> None:
        """Register callback for service unhealthy events."""
        self.registry.add_callback("service_unhealthy", callback)
    
    def on_service_healthy(self, callback: Callable[[ServiceInstance], None]) -> None:
        """Register callback for service healthy events."""
        self.registry.add_callback("service_healthy", callback)
    
    # Cleanup
    async def shutdown(self) -> None:
        """Shutdown the SDK and cleanup resources."""
        await self.deregister_current_service()
        await self.client_factory.close_all()
        await self.registry.shutdown()
        self.logger.info("Service SDK shutdown complete")


# Convenience Functions
async def register_service(
    service_name: str,
    version: str = "1.0.0",
    host: str = "0.0.0.0", 
    port: int = 8000,
    **kwargs
) -> None:
    """Quick service registration."""
    sdk = ServiceSDK()
    await sdk.register_current_service(
        service_name=service_name,
        version=version,
        host=host,
        port=port,
        **kwargs
    )


async def call_service(
    service_name: str,
    method: str = "GET",
    path: str = "",
    data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Any:
    """Quick service call."""
    sdk = ServiceSDK()
    return await sdk.call_service(
        service_name=service_name,
        method=method,
        path=path,
        data=data,
        **kwargs
    )


def get_service_client(service_name: str, **kwargs) -> ServiceClient:
    """Quick service client access."""
    sdk = ServiceSDK()
    return sdk.get_client(service_name, **kwargs)


# Global SDK instance
sdk = ServiceSDK() 