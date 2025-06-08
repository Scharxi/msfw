#!/usr/bin/env python3
"""
MSFW Inter-Service Communication SDK Demo
=========================================

Demonstrates how to use the MSFW SDK for microservice communication:

1. Service Registration & Discovery
2. HTTP Client with Circuit Breaker
3. Load Balancing & Health Checks
4. Type-safe API Communication
5. Batch Operations
6. Event-driven Communication
"""

import asyncio
import time
from typing import Optional
from contextlib import asynccontextmanager

from pydantic import BaseModel
from msfw import (
    ServiceSDK, ServiceClientError,
    call_service, register_service, get_service_client
)


# Example Data Models
class User(BaseModel):
    id: int
    name: str
    email: str


class CreateUserRequest(BaseModel):
    name: str
    email: str


class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


async def demo_service_registration():
    """Demo service registration and discovery."""
    print("🔧 Demo: Service Registration & Discovery")
    print("=" * 60)
    
    sdk = ServiceSDK()
    
    # Register multiple service instances
    await sdk.register_current_service(
        service_name="user-service",
        version="1.0.0",
        host="localhost",
        port=8001,
        metadata={"team": "backend", "region": "us-east-1"}
    )
    
    await sdk.register_external_service(
        service_name="user-service",
        host="localhost",
        port=8002,
        version="1.1.0",
        metadata={"team": "backend", "region": "us-west-1"}
    )
    
    await sdk.register_external_service(
        service_name="auth-service",
        host="localhost", 
        port=9001,
        version="2.0.0"
    )
    
    print("✅ Registered services:")
    
    # Discover services
    services = await sdk.list_all_services()
    for service_name, instances in services.items():
        print(f"\n🔍 {service_name}:")
        for instance in instances:
            for endpoint in instance.endpoints:
                print(f"  - {endpoint.url} (v{instance.version}) - {instance.status}")
                if instance.metadata:
                    print(f"    Metadata: {instance.metadata}")
    
    # Get specific service endpoint
    endpoint_url = await sdk.get_service_endpoint("user-service")
    print(f"\n🎯 Selected user-service endpoint: {endpoint_url}")
    
    print()


async def demo_http_client_communication():
    """Demo HTTP client with circuit breaker."""
    print("🌐 Demo: HTTP Client Communication")
    print("=" * 60)
    
    sdk = ServiceSDK()
    
    # Register a mock service for demonstration
    await sdk.register_external_service(
        service_name="api-service",
        host="httpbin.org",
        port=443,
        protocol="https"
    )
    
    print("📡 Making HTTP requests with circuit breaker protection...")
    
    try:
        # GET request
        print("\n1. GET Request:")
        response = await sdk.get_from_service(
            service_name="api-service",
            path="/json",
            timeout=10.0
        )
        print(f"   Response: {response}")
        
        # POST request
        print("\n2. POST Request:")
        post_data = {"name": "John Doe", "email": "john@example.com"}
        response = await sdk.post_to_service(
            service_name="api-service",
            path="/post",
            data=post_data,
            timeout=10.0
        )
        print(f"   Response keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
        
        # Using service client directly
        print("\n3. Direct Service Client:")
        async with sdk.service_client("api-service") as client:
            response = await client.get("/get", params={"test": "value"})
            print(f"   Status: Success")
            print(f"   Response type: {type(response)}")
        
    except ServiceClientError as e:
        print(f"❌ Service communication error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    print()


async def demo_type_safe_communication():
    """Demo type-safe API communication with Pydantic models."""
    print("🔒 Demo: Type-safe API Communication")
    print("=" * 60)
    
    sdk = ServiceSDK()
    
    # Register mock service
    await sdk.register_external_service(
        service_name="json-service",
        host="httpbin.org", 
        port=443,
        protocol="https"
    )
    
    try:
        print("📊 Type-safe requests with Pydantic models...")
        
        # Mock creating a user (httpbin.org echoes back the data)
        create_request = CreateUserRequest(name="Alice", email="alice@example.com")
        
        response = await sdk.call_service(
            service_name="json-service",
            method="POST",
            path="/post",
            data=create_request.model_dump(),
            response_model=ApiResponse,
            timeout=10.0
        )
        
        print(f"✅ Request successful!")
        print(f"   Response type: {type(response)}")
        if hasattr(response, 'json'):
            print(f"   Contains data: {bool(response.json)}")
        
    except Exception as e:
        print(f"❌ Error in type-safe communication: {e}")
    
    print()


async def demo_health_monitoring():
    """Demo service health monitoring."""
    print("💚 Demo: Service Health Monitoring")
    print("=" * 60)
    
    sdk = ServiceSDK()
    
    # Register some test services
    services_to_register = [
        ("healthy-service", "httpbin.org", 443, "https"),
        ("unknown-service", "nonexistent.example.com", 80, "http"),
    ]
    
    for name, host, port, protocol in services_to_register:
        await sdk.register_external_service(name, host, port, protocol=protocol)
    
    print("🏥 Checking service health...")
    
    # Check individual service health
    for service_name, _, _, _ in services_to_register:
        is_healthy = await sdk.check_service_health(service_name)
        status_icon = "✅" if is_healthy else "❌"
        print(f"   {status_icon} {service_name}: {'Healthy' if is_healthy else 'Unhealthy'}")
        
        # Get detailed status
        status = await sdk.get_service_status(service_name)
        print(f"      Instances: {status['instances']}, Healthy: {status['healthy_instances']}")
    
    # Batch health check
    print("\n🔍 Batch health check:")
    service_names = [name for name, _, _, _ in services_to_register]
    health_results = await sdk.check_multiple_services(service_names)
    
    for service_name, is_healthy in health_results.items():
        status_icon = "✅" if is_healthy else "❌" 
        print(f"   {status_icon} {service_name}: {'Healthy' if is_healthy else 'Unhealthy'}")
    
    print()


async def demo_batch_operations():
    """Demo batch service operations."""
    print("📦 Demo: Batch Operations")
    print("=" * 60)
    
    sdk = ServiceSDK()
    
    # Register test service
    await sdk.register_external_service(
        service_name="batch-service",
        host="httpbin.org",
        port=443,
        protocol="https"
    )
    
    print("🚀 Making concurrent service calls...")
    
    # Define multiple calls
    calls = [
        {
            "service_name": "batch-service",
            "method": "GET", 
            "path": "/json"
        },
        {
            "service_name": "batch-service",
            "method": "GET",
            "path": "/uuid"
        },
        {
            "service_name": "batch-service", 
            "method": "POST",
            "path": "/post",
            "data": {"batch": "operation", "id": 1}
        }
    ]
    
    try:
        start_time = time.time()
        results = await sdk.call_multiple_services(calls)
        end_time = time.time()
        
        print(f"✅ Completed {len(calls)} calls in {end_time - start_time:.2f}s")
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"   Call {i+1}: ❌ Error - {result}")
            else:
                print(f"   Call {i+1}: ✅ Success - {type(result)}")
                
    except Exception as e:
        print(f"❌ Batch operation error: {e}")
    
    print()


async def demo_event_callbacks():
    """Demo event-driven service communication."""
    print("📡 Demo: Event-driven Communication")
    print("=" * 60)
    
    sdk = ServiceSDK()
    
    # Event counters
    events = {"registered": 0, "deregistered": 0, "unhealthy": 0, "healthy": 0}
    
    # Register event callbacks
    def on_service_registered(service_instance):
        events["registered"] += 1
        print(f"🟢 Service registered: {service_instance.name} v{service_instance.version}")
    
    def on_service_deregistered(service_instance):
        events["deregistered"] += 1
        print(f"🔴 Service deregistered: {service_instance.name}")
    
    def on_service_unhealthy(service_instance):
        events["unhealthy"] += 1
        print(f"🟡 Service unhealthy: {service_instance.name}")
    
    def on_service_healthy(service_instance):
        events["healthy"] += 1
        print(f"🟢 Service healthy: {service_instance.name}")
    
    sdk.on_service_registered(on_service_registered)
    sdk.on_service_deregistered(on_service_deregistered)
    sdk.on_service_unhealthy(on_service_unhealthy)
    sdk.on_service_healthy(on_service_healthy)
    
    print("📺 Registered event callbacks, triggering events...")
    
    # Trigger events
    await sdk.register_external_service(
        service_name="event-service-1",
        host="localhost",
        port=8888
    )
    
    await sdk.register_external_service(
        service_name="event-service-2", 
        host="localhost",
        port=8889
    )
    
    # Deregister a service
    await sdk.registry.deregister_service("event-service-1")
    
    # Wait a moment for events to propagate
    await asyncio.sleep(0.1)
    
    print(f"\n📊 Event summary:")
    print(f"   Registered: {events['registered']}")
    print(f"   Deregistered: {events['deregistered']}")
    print(f"   Unhealthy: {events['unhealthy']}")
    print(f"   Healthy: {events['healthy']}")
    
    print()


async def demo_circuit_breaker():
    """Demo circuit breaker functionality."""
    print("⚡ Demo: Circuit Breaker Pattern")
    print("=" * 60)
    
    sdk = ServiceSDK()
    
    # Register a service that will fail
    await sdk.register_external_service(
        service_name="failing-service",
        host="nonexistent.localhost.invalid",
        port=8999
    )
    
    print("🔧 Testing circuit breaker with failing service...")
    
    # Configure aggressive circuit breaker for demo
    client = sdk.get_client(
        "failing-service",
        timeout=1.0,
        retry_attempts=2,
        failure_threshold=2,  # Open after 2 failures
        circuit_breaker=True
    )
    
    # Make failing requests
    for i in range(5):
        try:
            print(f"\n   Attempt {i+1}:")
            await client.get("/test", timeout=1.0)
            print(f"   ✅ Success")
        except ServiceClientError as e:
            error_type = type(e).__name__
            print(f"   ❌ {error_type}: {str(e)[:100]}...")
            
            # Check circuit state
            circuit_states = client.get_circuit_state()
            for endpoint, state in circuit_states.items():
                print(f"   🔌 Circuit {endpoint}: {state.state} (failures: {state.failure_count})")
        
        # Short delay between attempts
        await asyncio.sleep(0.5)
    
    print()


async def demo_convenience_functions():
    """Demo convenience functions."""
    print("🛠️  Demo: Convenience Functions")
    print("=" * 60)
    
    print("🚀 Using convenience functions for quick operations...")
    
    # Quick service registration
    await register_service(
        service_name="quick-service",
        version="1.0.0",
        host="localhost",
        port=8080
    )
    print("✅ Service registered using convenience function")
    
    # Quick service call (will fail since service doesn't exist)
    try:
        response = await call_service(
            service_name="httpbin.org",  # This won't work as expected, just for demo
            method="GET",
            path="/json",
            timeout=5.0
        )
        print(f"✅ Service call successful: {type(response)}")
    except Exception as e:
        print(f"❌ Service call failed (expected): {type(e).__name__}")
    
    # Quick client access
    client = get_service_client("quick-service")
    print(f"✅ Got service client: {type(client).__name__}")
    
    print()


@asynccontextmanager
async def demo_context():
    """Context manager for demo setup and cleanup."""
    print("🎯 MSFW Inter-Service Communication SDK")
    print("=" * 70)
    print("✨ Service Discovery & Registration")
    print("✨ HTTP Client with Circuit Breaker") 
    print("✨ Type-safe API Communication")
    print("✨ Health Monitoring & Batch Operations")
    print("✨ Event-driven Architecture")
    print()
    
    sdk = ServiceSDK()
    
    try:
        yield sdk
    finally:
        # Cleanup
        await sdk.shutdown()
        print("🧹 Cleanup completed")


async def main():
    """Run all SDK demos."""
    async with demo_context() as sdk:
        await demo_service_registration()
        await demo_http_client_communication()
        await demo_type_safe_communication()
        await demo_health_monitoring()
        await demo_batch_operations()
        await demo_event_callbacks()
        await demo_circuit_breaker()
        await demo_convenience_functions()
        
        print("🎉 SDK Demo Summary:")
        print("   • Service Discovery ✅")
        print("   • HTTP Client with Resilience Patterns ✅")
        print("   • Type-safe Communication ✅")  
        print("   • Health Monitoring ✅")
        print("   • Batch Operations ✅")
        print("   • Event-driven Architecture ✅")
        print("   • Circuit Breaker Protection ✅")
        print("   • Developer-friendly API ✅")
        print()
        print("🚀 Ready for production microservice communication!")


if __name__ == "__main__":
    asyncio.run(main()) 