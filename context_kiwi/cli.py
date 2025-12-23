#!/usr/bin/env python3
"""
Context Kiwi CLI Entry Point

Handles:
- First-run setup (~/.context-kiwi/ directory)
- Fetching core directives from registry
- Server modes (stdio, http)
"""

import argparse
import asyncio
import sys
from pathlib import Path

from context_kiwi import __version__, __package_name__


def get_user_dir() -> Path:
    """Get the user's Context Kiwi directory."""
    from context_kiwi.config import get_user_home
    return get_user_home()


def ensure_user_directory() -> bool:
    """
    Ensure ~/.context-kiwi/ exists with proper structure.
    
    Creates on first run:
    ~/.context-kiwi/
    ├── config.yaml
    ├── directives/
    │   └── core/
    └── cache/
    
    Returns True if this was first run (new install).
    """
    user_dir = get_user_dir()
    
    if user_dir.exists():
        return False  # Already set up
    
    print(f"🥝 First run! Setting up {user_dir}")
    
    # Create directory structure
    user_dir.mkdir(parents=True)
    (user_dir / "directives" / "core").mkdir(parents=True)
    (user_dir / "cache").mkdir()
    
    # Create default config
    config_content = """\
# Context Kiwi Configuration
# ~/.context-kiwi/config.yaml

# Registry settings
registry:
  # url: https://your-registry-url.com  # Optional, if using custom registry
  # api_key: your-api-key  # Optional, for publishing

# Local settings
local:
  log_level: INFO
  analytics: true  # Log runs to .ai/.runs/

# Default inputs for directives
defaults:
  # author: "Your Name"
"""
    (user_dir / "config.yaml").write_text(config_content)
    print(f"  ✓ Created config.yaml")
    print(f"  ✓ Created directory structure")
    
    return True  # First run


async def fetch_core_directives():
    """
    Fetch core directives from Supabase registry.
    
    Core directives downloaded on first run:
    - init: Initialize a project
    - create_directive: Create new directives
    """
    print("\n📦 Fetching core directives from registry...")
    
    try:
        import httpx
        from context_kiwi.config import get_supabase_url, get_supabase_key
        
        supabase_url = get_supabase_url()
        api_key = get_supabase_key()
        core_directives = ["init", "create_directive"]
        
        user_dir = get_user_dir()
        
        headers = {
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}"
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            for name in core_directives:
                try:
                    # Get directive ID
                    dir_resp = await client.get(
                        f"{supabase_url}/rest/v1/directives",
                        params={"name": f"eq.{name}", "select": "id"},
                        headers=headers
                    )
                    
                    if dir_resp.status_code != 200 or not dir_resp.json():
                        print(f"  ⚠ Could not find {name}")
                        continue
                    
                    directive_id = dir_resp.json()[0]["id"]
                    
                    # Get latest version content
                    ver_resp = await client.get(
                        f"{supabase_url}/rest/v1/directive_versions",
                        params={
                            "directive_id": f"eq.{directive_id}",
                            "is_latest": "eq.true",
                            "select": "content"
                        },
                        headers=headers
                    )
                    
                    if ver_resp.status_code == 200 and ver_resp.json():
                        content = ver_resp.json()[0]["content"]
                        dest = user_dir / "directives" / "core" / f"{name}.md"
                        dest.write_text(content)
                        print(f"  ✓ Downloaded {name}")
                    else:
                        print(f"  ⚠ Could not fetch {name} content")
                        
                except Exception as e:
                    print(f"  ⚠ Could not fetch {name}: {e}")
        
        print("")
        
    except ImportError:
        print("  ⚠ httpx not available, skipping directive fetch")
        print("  → Run: get('init') to fetch core directives manually")
    except Exception as e:
        print(f"  ⚠ Could not connect to registry: {e}")
        print("  → Run: get('init') to fetch core directives manually")


def print_version():
    """Print version info."""
    print(f"{__package_name__} v{__version__}")


def print_first_run_help():
    """Print help after first run setup."""
    print("""✓ Context Kiwi ready!

Next steps:
  1. Add to your MCP config (.cursor/mcp.json):
     
     {
       "mcpServers": {
         "context-kiwi": {
           "command": "context-kiwi"
         }
       }
     }

  2. In Cursor, ask: "Initialize this project for Context Kiwi"
     → This runs the init directive to create .ai/

  3. Search for directives: search("jwt auth")
  4. Run directives: run("jwt_auth_zustand")

Documentation: https://github.com/YOUR_USERNAME/context-kiwi
""")


async def run_stdio():
    """Run in stdio mode (for Cursor/Claude Desktop)."""
    from context_kiwi.server import CodeKiwiMCPServer
    server = CodeKiwiMCPServer()
    await server.start()


async def run_http(port: int):
    """Run in HTTP mode."""
    import os
    os.environ["MCP_PORT"] = str(port)
    from context_kiwi.server_http import main as http_main
    await http_main()


async def main_async(args):
    """Async main to handle first-run setup."""
    # First-run setup
    if not args.skip_setup:
        is_first_run = ensure_user_directory()
        
        if is_first_run:
            # Fetch core directives from registry
            await fetch_core_directives()
            print_first_run_help()
            
            # If just setting up, don't start server unless explicitly asked
            if not (args.http or args.stdio):
                return
    
    # Run server
    if args.http:
        await run_http(args.port)
    else:
        # Default to stdio
        await run_stdio()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="context-kiwi",
        description="🥝 Context Kiwi - Directive-based code generation MCP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  context-kiwi              Run in stdio mode (default, for Cursor)
  context-kiwi --http       Run HTTP server on port 8000
  context-kiwi --http --port 3000   Run HTTP server on port 3000

MCP Configuration (.cursor/mcp.json):
  
  {
    "mcpServers": {
      "context-kiwi": {
        "command": "context-kiwi"
      }
    }
  }

  Or with uvx (no install needed):
  
  {
    "mcpServers": {
      "context-kiwi": {
        "command": "uvx",
        "args": ["context-kiwi"]
      }
    }
  }
"""
    )
    
    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="Show version and exit"
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Run in stdio mode (default)"
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run in HTTP mode"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8000,
        help="HTTP port (default: 8000)"
    )
    parser.add_argument(
        "--skip-setup",
        action="store_true",
        help="Skip first-run setup"
    )
    
    args = parser.parse_args()
    
    if args.version:
        print_version()
        sys.exit(0)
    
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
