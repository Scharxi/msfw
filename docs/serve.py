#!/usr/bin/env python3
"""
Simple HTTP server to serve the built Sphinx documentation locally.
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

def serve_docs(port=8000):
    """Serve the documentation on the specified port."""
    
    # Change to the HTML build directory
    html_dir = Path(__file__).parent / "_build" / "html"
    
    if not html_dir.exists():
        print("❌ Documentation not built yet. Run 'make html' first.")
        return
    
    os.chdir(html_dir)
    
    # Create server
    handler = http.server.SimpleHTTPRequestHandler
    
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"🚀 Serving documentation at http://localhost:{port}")
            print(f"📁 Serving from: {html_dir}")
            print("Press Ctrl+C to stop the server")
            
            # Try to open browser
            try:
                webbrowser.open(f"http://localhost:{port}")
            except:
                pass
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {port} is already in use. Try a different port:")
            print(f"   python serve.py --port {port + 1}")
        else:
            print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Serve Sphinx documentation locally")
    parser.add_argument("--port", "-p", type=int, default=8000, 
                       help="Port to serve on (default: 8000)")
    
    args = parser.parse_args()
    serve_docs(args.port) 