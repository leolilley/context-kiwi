#!/usr/bin/env python3
"""
Context Kiwi MCP Server - HTTP Transport
Runs as a web server using MCP Streamable HTTP protocol.

This is the production entry point for Fly.io deployment.
For local dev, use `python -m src.server --stdio` instead.
"""

import asyncio
import os
import uuid

from mcp.server.streamable_http import StreamableHTTPServerTransport
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse, PlainTextResponse

from context_kiwi.server import CodeKiwiMCPServer
from context_kiwi import __version__

# Configuration
HOST = os.getenv("MCP_HOST", "0.0.0.0")
PORT = int(os.getenv("MCP_PORT", "8000"))

# Global server instance and transports
mcp_server_instance = None
active_transports = {}  # session_id -> transport mapping


async def initialize_mcp_server():
    """Initialize the MCP server instance (shared initialization logic)."""
    global mcp_server_instance
    if mcp_server_instance is None:
        mcp_server_instance = CodeKiwiMCPServer()
        await mcp_server_instance.config.load()
        mcp_server_instance._register_core_tools()
        
        tool_count = len(mcp_server_instance.tool_registry.listTools())
        mcp_server_instance.logger.info(f"MCP Server initialized with {tool_count} tools")
    
    return mcp_server_instance


async def mcp_endpoint(scope, receive, send):
    """
    Handle MCP requests via Streamable HTTP protocol.
    This endpoint handles all MCP communication (GET/POST/DELETE).
    """
    request_path = scope.get("path", "")
    path_parts = request_path.strip("/").split("/")
    
    # Extract session ID from path like /mcp/session-id or create new session
    if len(path_parts) >= 2:
        session_id = path_parts[1]
    else:
        session_id = str(uuid.uuid4())
    
    # Get or create transport for this session
    if session_id not in active_transports:
        server_instance = await initialize_mcp_server()
        transport = StreamableHTTPServerTransport(mcp_session_id=session_id)
        
        # connect() returns streams, then we run the server with them
        async with transport.connect() as (read_stream, write_stream):
            active_transports[session_id] = transport
            # Start server.run in background task so we can handle requests
            asyncio.create_task(
                server_instance.server.run(
                    read_stream,
                    write_stream,
                    server_instance.server.create_initialization_options(),
                )
            )
            await transport.handle_request(scope, receive, send)
    else:
        transport = active_transports[session_id]
        await transport.handle_request(scope, receive, send)


async def health_check(request):
    """Health check endpoint."""
    server_instance = await initialize_mcp_server()
    tool_count = len(server_instance.tool_registry.listTools())
    return PlainTextResponse(
        f"Context Kiwi MCP Server (HTTP)\n"
        f"Version: {__version__}\n"
        f"Status: Running\n"
        f"Tools: {tool_count}\n"
        f"MCP endpoint: /mcp/{{session-id}}\n"
    )


async def get_directive(request):
    """Serve a directive file by name and optional version (JSON response)."""
    from context_kiwi.registry.download import serve_directive, get_directive_info
    
    name = request.path_params.get("name", "")
    version = request.query_params.get("version", None)
    
    try:
        content = await serve_directive(name, version)
        info = await get_directive_info(name)
        return JSONResponse({
            "directive": content, 
            "name": name,
            "version": info["latest_version"] if info else None,
            "available_versions": info["available_versions"] if info else [],
        })
    except FileNotFoundError:
        return JSONResponse({"error": f"Directive not found: {name}"}, status_code=404)
    except RuntimeError as e:
        return JSONResponse({"error": str(e)}, status_code=503)


async def get_directive_raw(request):
    """Serve raw directive content for direct curl download.
    
    Usage: curl -sL https://context-kiwi.fly.dev/d/create_directive.md -o .ai/directives/core/create_directive.md
    """
    from context_kiwi.registry.download import serve_directive
    from starlette.responses import Response
    
    name = request.path_params.get("name", "")
    # Strip .md extension if present
    if name.endswith(".md"):
        name = name[:-3]
    
    version = request.query_params.get("v", None)
    
    try:
        content = await serve_directive(name, version)
        return Response(
            content=content,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f"inline; filename={name}.md"}
        )
    except FileNotFoundError:
        return PlainTextResponse(f"Directive not found: {name}", status_code=404)
    except RuntimeError as e:
        return PlainTextResponse(f"Error: {str(e)}", status_code=503)


# Create Starlette app
# 
# Endpoints:
# - /mcp/{session} - MCP protocol (all tool interaction)
# - /health - Deployment health check
# - /d/{name}.md - Raw directive download (for curl)
# - /directives/core/{name} - JSON directive info (legacy)
#
# Everything else goes through MCP tools (search_tool, execute, help)
app = Starlette(
    routes=[
        Route("/health", endpoint=health_check),
        Route("/d/{name}", endpoint=get_directive_raw),  # Raw download: curl -o file.md /d/name.md
        Route("/directives/core/{name}", endpoint=get_directive),  # JSON response (legacy)
        Mount("/mcp", app=mcp_endpoint),  # MCP protocol - all tool interaction
    ],
)


async def main():
    """Run the HTTP server."""
    import uvicorn
    
    config = uvicorn.Config(
        app,
        host=HOST,
        port=PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)
    
    print(f"Context Kiwi MCP Server (HTTP) starting on http://{HOST}:{PORT}")
    print(f"")
    print(f"Endpoints:")
    print(f"  MCP:      http://{HOST}:{PORT}/mcp/{{session-id}}  (all tool interaction)")
    print(f"  Health:   http://{HOST}:{PORT}/health")
    print(f"  Download: http://{HOST}:{PORT}/d/{{name}}.md  (raw curl download)")
    print(f"")
    print(f"To connect from Cursor, add to mcp.json:")
    print(f'  "url": "http://{HOST}:{PORT}/mcp/dev-session"')
    
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())

