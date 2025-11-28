import os
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

from mcp.server.fastmcp import FastMCP

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

# Base directory for JS scripts (configure via env from your MCP host)
SCRIPTS_DIR = Path(os.environ.get("SCRIPTS_DIR", "./scripts")).resolve()
SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

mcp = FastMCP("JS Scripts Server")


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _safe_script_path(filename: str) -> Path:
    """
    Resolve a JS file inside SCRIPTS_DIR, preventing directory traversal.
    Only allows `.js` files.
    """
    if not filename.endswith(".js"):
        raise ValueError("Only .js files are allowed")

    # Normalize and resolve
    path = (SCRIPTS_DIR / filename).resolve()

    # Prevent escaping the scripts directory (e.g. ../../etc/passwd)
    if not str(path).startswith(str(SCRIPTS_DIR)):
        raise ValueError("Invalid path (outside SCRIPTS_DIR)")

    return path


# -------------------------------------------------------------------
# Tools
# -------------------------------------------------------------------

@mcp.tool()
def list_scripts() -> List[str]:
    """
    List all .js files in the scripts directory.
    """
    files = []
    for p in SCRIPTS_DIR.glob("*.js"):
        if p.is_file():
            # return paths relative to SCRIPTS_DIR
            files.append(p.name)
    return files


@mcp.tool()
def read_script(filename: str) -> str:
    """
    Read the contents of a JS file inside SCRIPTS_DIR.
    """
    path = _safe_script_path(filename)

    if not path.exists():
        raise FileNotFoundError(f"Script not found: {filename}")

    return path.read_text(encoding="utf-8")


@mcp.tool()
def write_script(
    filename: str,
    content: str,
    overwrite: bool = True,
) -> str:
    """
    Write or update a JS file inside SCRIPTS_DIR.

    - filename: name of the JS file (e.g., "test.js")
    - content: full file content
    - overwrite: if False and file exists, raises an error
    """
    path = _safe_script_path(filename)

    if path.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {filename}")

    path.write_text(content, encoding="utf-8")
    return f"Wrote {filename} ({len(content)} bytes)"


@mcp.tool()
def execute_script(
    filename: str,
    args: Optional[List[str]] = None,
    timeout_seconds: int = 30,
) -> Dict[str, Any]:
    """
    Execute a JS file with Deno.

    - filename: JS file to execute (must be inside SCRIPTS_DIR)
    - args: optional CLI arguments passed to the script
    - timeout_seconds: kill the process if it runs too long

    Returns:
      {
        "command": [...],
        "returncode": int,
        "stdout": "...",
        "stderr": "..."
      }
    """
    if args is None:
        args = []

    path = _safe_script_path(filename)

    if not path.exists():
        raise FileNotFoundError(f"Script not found: {filename}")

    # You can tighten permissions here if needed.
    # For parity with your Deno.Command example, this uses allow-all.
    cmd = [
        "deno",
        "run",
        "--allow-all",
        str(path),
        *args,
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(SCRIPTS_DIR),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as e:
        return {
            "command": cmd,
            "error": "timeout",
            "timeout_seconds": timeout_seconds,
            "stdout": e.stdout or "",
            "stderr": e.stderr or "",
        }
    except FileNotFoundError:
        # `deno` not installed / not on PATH
        return {
            "command": cmd,
            "error": "deno_not_found",
            "message": "Deno executable not found. Is it installed and on PATH?",
        }
    except Exception as e:
        return {
            "command": cmd,
            "error": "execution_failed",
            "message": str(e),
        }

    return {
        "command": cmd,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


# -------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------

if __name__ == "__main__":
    # For Claude Desktop / Cursor / OpenAI MCP hosts that spawn via stdio
    mcp.run(transport="stdio")
