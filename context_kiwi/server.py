#!/usr/bin/env python3
"""
Context Kiwi MCP Server
Main server implementation following proper MCP architecture.
"""

import argparse
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel import NotificationOptions
from mcp import types
from context_kiwi import __version__, __package_name__
from context_kiwi.config import ConfigManager
from context_kiwi.utils import Logger
from context_kiwi.tools import ToolRegistry, SearchTool, RunTool, GetTool, PublishTool, DeleteTool, HelpTool


class CodeKiwiMCPServer:
    """Main MCP Server for Context Kiwi."""
    
    def __init__(self):
        # Initialize configuration
        self.config = ConfigManager()
        config = self.config.get()
        
        # Initialize MCP Server
        self.server = Server(__package_name__)
        
        # Server capabilities
        self.capabilities = {
            "tools": {"listChanged": True},
            "logging": {},
        }
        
        # Initialize logger
        self.logger = Logger(name=__package_name__, level=config.log_level)
        
        # Initialize tool registry
        self.tool_registry = ToolRegistry(self.logger)
        
        # Set up MCP protocol handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up MCP protocol request handlers using decorators."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List available tools - exposes 5 core tools."""
            try:
                core_tool_names = ["search", "run", "get", "publish", "delete", "help"]
                all_tools = self.tool_registry.getToolSchemas()
                tools = [t for t in all_tools if t.name in core_tool_names]
                self.logger.debug(f"Exposing {len(tools)} core tools")
                return tools
            except Exception as e:
                self.logger.error(f"Error listing tools: {e}")
                return []
        
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, 
            arguments: dict
        ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """Execute a tool - MCP tools/call handler."""
            try:
                if not self.tool_registry.hasTool(name):
                    raise ValueError(f"Tool '{name}' not found")
                
                # Create context
                from context_kiwi.mcp_types import ToolContext
                context = ToolContext(
                    userId="system",
                    requestId=f"req_{asyncio.get_event_loop().time()}",
                    permissions=["execute", "read", "write"],
                    accessLevel="read-write",
                    timestamp=asyncio.get_event_loop().time(),
                    toolName=name
                )
                
                result = await self.tool_registry.execute(name, arguments, context)
                
                if result.success and result.result:
                    content = []
                    for content_item in result.result.content:
                        text = content_item.text.strip()
                        content.append(types.TextContent(type="text", text=text))
                    return content
                else:
                    error_msg = result.error.message if result.error else "Unknown error"
                    raise RuntimeError(f"Tool execution failed: {error_msg}")
            
            except ValueError as e:
                self.logger.error(f"Tool not found: {e}")
                raise
            except Exception as e:
                self.logger.error(f"Tool execution error: {e}")
                raise RuntimeError(f"Internal error: {str(e)}") from e
    
    def _register_core_tools(self):
        """Register the 5 core tools."""
        # Initialize core tools
        tools = [
            SearchTool(self.logger),
            RunTool(self.logger),
            GetTool(self.logger),
            PublishTool(self.logger),
            DeleteTool(self.logger),
            HelpTool(self.logger),
        ]
        
        # Register each tool
        for tool in tools:
            self.tool_registry.register(tool)
            self.tool_registry.registerHandler(tool.name, tool.execute)
        
        self.logger.info("Registered 6 core tools: search, run, get, publish, delete, help")
    
    async def start(self):
        """Start the MCP server."""
        try:
            # Load configuration
            await self.config.load()
            
            # Register tools
            self._register_core_tools()
            
            tool_count = len(self.tool_registry.listTools())
            self.logger.info(f"Registered {tool_count} tools")
            
            # Create transport and run server
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name=__package_name__,
                        server_version=__version__,
                        capabilities=self.server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={}
                        ),
                    ),
                )
            
            self.logger.info("Context Kiwi MCP Server started successfully")
        
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            raise


async def run_stdio():
    """Run in stdio mode (for Cursor connection)."""
    server = CodeKiwiMCPServer()
    await server.start()


async def run_http(port: int):
    """Run in HTTP mode using Streamable HTTP transport.
    
    This delegates to server_http.py which uses Starlette + StreamableHTTPServerTransport.
    """
    import os
    os.environ["MCP_PORT"] = str(port)
    
    from context_kiwi.server_http import main as http_main
    await http_main()


def main():
    parser = argparse.ArgumentParser(description="Context Kiwi MCP Server")
    parser.add_argument("--stdio", action="store_true", help="Run in stdio mode")
    parser.add_argument("--http", action="store_true", help="Run in HTTP mode")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port")
    args = parser.parse_args()
    
    if args.http:
        asyncio.run(run_http(args.port))
    else:
        asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
