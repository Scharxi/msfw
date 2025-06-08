"""
Example Logging Plugin for MSFW
===============================

This demonstrates how to create a plugin that:
- Hooks into application events
- Provides enhanced logging capabilities
- Registers multiple event handlers
- Can be configured via the main config
"""

import json
import time
from datetime import datetime
from typing import Any, Dict

from msfw import Plugin, Config


class EnhancedLoggingPlugin(Plugin):
    """Plugin that provides enhanced logging capabilities."""
    
    def __init__(self):
        super().__init__()
        self.request_count = 0
        self.start_time = None
        self.request_times = []
    
    @property
    def name(self) -> str:
        return "enhanced_logging"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Enhanced logging plugin with request tracking and performance metrics"
    
    @property
    def author(self) -> str:
        return "MSFW Team"
    
    @property
    def priority(self) -> int:
        return 10  # High priority for logging
    
    async def setup(self, config: Config) -> None:
        """Setup the plugin."""
        print(f"🔌 Setting up {self.name} plugin")
        
        # Register event handlers
        self.register_hook("app_startup", self.on_app_startup)
        self.register_hook("app_shutdown", self.on_app_shutdown)
        self.register_hook("before_request", self.on_before_request)
        self.register_hook("after_request", self.on_after_request)
        self.register_hook("user_login", self.on_user_login)
        
        # Initialize timing
        self.start_time = time.time()
        
        print(f"✅ Enhanced logging plugin configured successfully")
    
    async def cleanup(self) -> None:
        """Cleanup the plugin."""
        print(f"🧹 Cleaning up {self.name} plugin")
        
        # Print final statistics
        if self.start_time:
            uptime = time.time() - self.start_time
            print(f"📊 Application Statistics:")
            print(f"   - Uptime: {uptime:.2f} seconds")
            print(f"   - Total requests: {self.request_count}")
            
            if self.request_times:
                avg_time = sum(self.request_times) / len(self.request_times)
                print(f"   - Average request time: {avg_time:.3f}s")
                print(f"   - Min request time: {min(self.request_times):.3f}s")
                print(f"   - Max request time: {max(self.request_times):.3f}s")
    
    async def on_app_startup(self, **kwargs):
        """Handle application startup."""
        app = kwargs.get("app")
        timestamp = datetime.now().isoformat()
        
        startup_info = {
            "event": "app_startup",
            "timestamp": timestamp,
            "plugin": self.name,
            "message": "Application started successfully",
            "app_title": getattr(app, "title", "Unknown") if app else "Unknown"
        }
        
        print(f"🚀 {json.dumps(startup_info, indent=2)}")
    
    async def on_app_shutdown(self, **kwargs):
        """Handle application shutdown."""
        timestamp = datetime.now().isoformat()
        
        shutdown_info = {
            "event": "app_shutdown",
            "timestamp": timestamp,
            "plugin": self.name,
            "message": "Application shutdown initiated",
            "total_requests_processed": self.request_count
        }
        
        print(f"🛑 {json.dumps(shutdown_info, indent=2)}")
    
    async def on_before_request(self, request=None, **kwargs):
        """Handle before request processing."""
        if request:
            # Store request start time
            if not hasattr(request.state, "start_time"):
                request.state.start_time = time.time()
            
            request_info = {
                "event": "before_request",
                "timestamp": datetime.now().isoformat(),
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
                "plugin": self.name
            }
            
            print(f"📥 {json.dumps(request_info)}")
    
    async def on_after_request(self, request=None, response=None, **kwargs):
        """Handle after request processing."""
        self.request_count += 1
        
        if request and response:
            # Calculate request duration
            duration = None
            if hasattr(request.state, "start_time"):
                duration = time.time() - request.state.start_time
                self.request_times.append(duration)
            
            response_info = {
                "event": "after_request",
                "timestamp": datetime.now().isoformat(),
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "duration_seconds": duration,
                "request_count": self.request_count,
                "plugin": self.name
            }
            
            print(f"📤 {json.dumps(response_info)}")
    
    async def on_user_login(self, user_id=None, username=None, **kwargs):
        """Handle user login events."""
        login_info = {
            "event": "user_login",
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "username": username,
            "plugin": self.name,
            "message": f"User {username or user_id} logged in successfully"
        }
        
        print(f"👤 {json.dumps(login_info, indent=2)}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current plugin statistics."""
        current_time = time.time()
        uptime = current_time - self.start_time if self.start_time else 0
        
        stats = {
            "plugin": self.name,
            "version": self.version,
            "uptime_seconds": uptime,
            "total_requests": self.request_count,
            "requests_per_second": self.request_count / uptime if uptime > 0 else 0,
        }
        
        if self.request_times:
            stats.update({
                "average_request_time": sum(self.request_times) / len(self.request_times),
                "min_request_time": min(self.request_times),
                "max_request_time": max(self.request_times),
            })
        
        return stats 