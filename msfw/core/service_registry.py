"""Service Registry for microservice discovery and communication."""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

from pydantic import BaseModel


class ServiceStatus(str, Enum):
    """Service status enumeration."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"
    UNKNOWN = "unknown"


@dataclass
class ServiceEndpoint:
    """Service endpoint information."""
    host: str
    port: int
    protocol: str = "http"
    path: str = ""
    weight: int = 100
    
    @property
    def url(self) -> str:
        """Get the full URL for this endpoint."""
        base_url = f"{self.protocol}://{self.host}:{self.port}"
        if self.path and not self.path.startswith("/"):
            self.path = f"/{self.path}"
        return f"{base_url}{self.path}"


@dataclass 
class ServiceInstance:
    """Service instance information."""
    name: str
    version: str
    endpoints: List[ServiceEndpoint]
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ServiceStatus = ServiceStatus.HEALTHY
    last_heartbeat: float = field(default_factory=time.time)
    health_check_url: Optional[str] = None
    
    def __post_init__(self):
        """Set default health check URL if not provided."""
        if not self.health_check_url and self.endpoints:
            primary_endpoint = self.endpoints[0]
            self.health_check_url = f"{primary_endpoint.url}/health"


class ServiceRegistry:
    """Central service registry for microservice discovery."""
    
    def __init__(self):
        self._services: Dict[str, List[ServiceInstance]] = {}
        self._health_check_interval = 30  # seconds
        self._health_check_timeout = 5    # seconds
        self._service_ttl = 90           # seconds
        self._health_check_task: Optional[asyncio.Task] = None
        self._callbacks: Dict[str, List[Callable]] = {
            "service_registered": [],
            "service_deregistered": [],
            "service_unhealthy": [],
            "service_healthy": []
        }
        self.logger = logging.getLogger(__name__)
    
    async def register_service(
        self, 
        service: ServiceInstance,
        auto_heartbeat: bool = True
    ) -> None:
        """Register a service instance."""
        if service.name not in self._services:
            self._services[service.name] = []
        
        # Remove existing instance with same endpoints
        self._services[service.name] = [
            s for s in self._services[service.name] 
            if not self._same_endpoints(s.endpoints, service.endpoints)
        ]
        
        # Add new instance
        service.last_heartbeat = time.time()
        self._services[service.name].append(service)
        
        self.logger.info(f"Registered service: {service.name} v{service.version}")
        await self._trigger_callback("service_registered", service)
        
        # Start health checking if not already running
        if auto_heartbeat and not self._health_check_task:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def deregister_service(
        self, 
        service_name: str, 
        endpoints: Optional[List[ServiceEndpoint]] = None
    ) -> None:
        """Deregister a service instance."""
        if service_name not in self._services:
            return
        
        if endpoints:
            # Remove specific instance
            removed = []
            self._services[service_name] = [
                s for s in self._services[service_name]
                if not self._same_endpoints(s.endpoints, endpoints) or removed.append(s)
            ]
            for service in removed:
                await self._trigger_callback("service_deregistered", service)
        else:
            # Remove all instances of service
            for service in self._services[service_name]:
                await self._trigger_callback("service_deregistered", service)
            del self._services[service_name]
        
        self.logger.info(f"Deregistered service: {service_name}")
    
    async def discover_service(
        self, 
        service_name: str,
        version: Optional[str] = None
    ) -> List[ServiceInstance]:
        """Discover healthy instances of a service, optionally filtered by version."""
        if service_name not in self._services:
            return []
        
        healthy_services = [
            s for s in self._services[service_name] 
            if s.status == ServiceStatus.HEALTHY
        ]
        
        # Filter by version if specified
        if version:
            from msfw.core.versioning import VersionInfo
            try:
                requested_version = VersionInfo.from_string(version)
                version_filtered = []
                
                for service in healthy_services:
                    service_version = VersionInfo.from_string(service.version)
                    # Include services with compatible versions
                    if (service_version == requested_version or 
                        service_version.is_compatible_with(requested_version)):
                        version_filtered.append(service)
                
                return version_filtered
            except ValueError:
                # If version parsing fails, return all healthy services
                pass
        
        return healthy_services
    
    async def get_service_endpoint(
        self, 
        service_name: str,
        version: Optional[str] = None,
        load_balancer: str = "round_robin"
    ) -> Optional[ServiceEndpoint]:
        """Get a service endpoint using specified load balancing and version."""
        services = await self.discover_service(service_name, version=version)
        if not services:
            return None
        
        if load_balancer == "round_robin":
            # Simple round-robin (stateless)
            service = services[int(time.time()) % len(services)]
        elif load_balancer == "weighted":
            # Weighted selection based on endpoint weights
            service = self._weighted_selection(services)
        else:
            # Default to first healthy service
            service = services[0]
        
        return service.endpoints[0] if service.endpoints else None
    
    def _weighted_selection(self, services: List[ServiceInstance]) -> ServiceInstance:
        """Select service based on endpoint weights."""
        total_weight = sum(
            sum(ep.weight for ep in service.endpoints) 
            for service in services
        )
        
        if total_weight == 0:
            return services[0]
        
        import random
        weight = random.randint(1, total_weight)
        
        for service in services:
            service_weight = sum(ep.weight for ep in service.endpoints)
            weight -= service_weight
            if weight <= 0:
                return service
        
        return services[0]
    
    async def heartbeat(self, service_name: str, endpoints: List[ServiceEndpoint]) -> None:
        """Update service heartbeat."""
        if service_name not in self._services:
            return
        
        for service in self._services[service_name]:
            if self._same_endpoints(service.endpoints, endpoints):
                service.last_heartbeat = time.time()
                if service.status != ServiceStatus.HEALTHY:
                    service.status = ServiceStatus.HEALTHY
                    await self._trigger_callback("service_healthy", service)
                break
    
    async def list_services(self) -> Dict[str, List[ServiceInstance]]:
        """List all registered services."""
        return self._services.copy()
    
    def add_callback(self, event: str, callback: Callable) -> None:
        """Add callback for service events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    async def _health_check_loop(self) -> None:
        """Background health checking loop."""
        import aiohttp
        
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self._health_check_timeout)
                ) as session:
                    
                    for service_name, instances in self._services.items():
                        for service in instances[:]:  # Copy to avoid modification during iteration
                            # Check TTL
                            if time.time() - service.last_heartbeat > self._service_ttl:
                                self.logger.warning(f"Service {service_name} TTL expired")
                                instances.remove(service)
                                await self._trigger_callback("service_deregistered", service)
                                continue
                            
                            # Health check
                            if service.health_check_url:
                                try:
                                    async with session.get(service.health_check_url) as resp:
                                        if resp.status == 200:
                                            if service.status != ServiceStatus.HEALTHY:
                                                service.status = ServiceStatus.HEALTHY
                                                await self._trigger_callback("service_healthy", service)
                                        else:
                                            if service.status == ServiceStatus.HEALTHY:
                                                service.status = ServiceStatus.UNHEALTHY
                                                await self._trigger_callback("service_unhealthy", service)
                                except Exception as e:
                                    if service.status == ServiceStatus.HEALTHY:
                                        service.status = ServiceStatus.UNHEALTHY
                                        await self._trigger_callback("service_unhealthy", service)
                                        self.logger.warning(f"Health check failed for {service_name}: {e}")
                        
                        # Clean up empty service lists
                        if not instances:
                            del self._services[service_name]
                            
            except Exception as e:
                self.logger.error(f"Health check loop error: {e}")
    
    async def _trigger_callback(self, event: str, service: ServiceInstance) -> None:
        """Trigger callbacks for service events."""
        for callback in self._callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(service)
                else:
                    callback(service)
            except Exception as e:
                self.logger.error(f"Callback error for {event}: {e}")
    
    def _same_endpoints(self, endpoints1: List[ServiceEndpoint], endpoints2: List[ServiceEndpoint]) -> bool:
        """Check if two endpoint lists are the same."""
        if len(endpoints1) != len(endpoints2):
            return False
        
        for ep1 in endpoints1:
            found = False
            for ep2 in endpoints2:
                if ep1.host == ep2.host and ep1.port == ep2.port:
                    found = True
                    break
            if not found:
                return False
        
        return True
    
    async def shutdown(self) -> None:
        """Shutdown the service registry."""
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass  # Ignore other exceptions during shutdown
        self._health_check_task = None


# Global service registry instance
service_registry = ServiceRegistry() 