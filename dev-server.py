#!/usr/bin/env python3
"""
Simple development HTTP server with CORS support.
Serves files from the current directory on http://localhost:8000
"""

import http.server
import socketserver
from http import HTTPStatus

PORT = 8000

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with CORS headers."""

    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        """Handle preflight requests."""
        self.send_response(HTTPStatus.OK)
        self.end_headers()

    def log_message(self, format, *args):
        """Custom log message format."""
        print(f"[{self.log_date_time_string()}] {format % args}")

def main():
    with socketserver.TCPServer(("", PORT), CORSRequestHandler) as httpd:
        print(f"╔════════════════════════════════════════════════════════╗")
        print(f"║  WebGPU Audio Waterfall - Development Server          ║")
        print(f"╠════════════════════════════════════════════════════════╣")
        print(f"║  Server running at:                                    ║")
        print(f"║  http://localhost:{PORT}                                   ║")
        print(f"║                                                        ║")
        print(f"║  Open in browser:                                      ║")
        print(f"║  http://localhost:{PORT}/webgpu-audio-waterfall.html       ║")
        print(f"║                                                        ║")
        print(f"║  Press Ctrl+C to stop                                  ║")
        print(f"╚════════════════════════════════════════════════════════╝")
        print()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nShutting down server...")
            httpd.shutdown()

if __name__ == "__main__":
    main()
