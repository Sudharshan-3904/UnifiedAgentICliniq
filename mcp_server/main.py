#!/usr/bin/env python3
"""
MCP Server for JavaScript file operations using MCPServer
Provides tools to create, read, write, and execute JavaScript files with Deno
Integrated AI-powered code generation and analysis using Gemini API
"""

import asyncio
import subprocess
import os
from pathlib import Path
from typing import Optional
from google import genai
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("javascript-file-server")

# Base directory for JS files
BASE_DIR = Path("./js_files")
BASE_DIR.mkdir(exist_ok=True)

# Initialize Gemini client (gets API key from GEMINI_API_KEY environment variable)
try:
    gemini_client = genai.Client()    
    GEMINI_AVAILABLE = True
except Exception:
    gemini_client = None
    GEMINI_AVAILABLE = False


def resolve_path(filename: str) -> Path:
    """Resolve and validate file path within base directory"""
    path = (BASE_DIR / filename).resolve()
    if not str(path).startswith(str(BASE_DIR.resolve())):
        raise ValueError("Path traversal not allowed")
    return path


def is_code_content(content: str) -> bool:
    """Determine if content appears to be actual code vs a prompt"""
    code_indicators = [
        'function ', 'const ', 'let ', 'var ', 'class ', 
        'import ', 'export ', 'async ', 'await ',
        '=>', '{}', '();', 'console.', 'return ',
        '//', '/*', '*/'
    ]
    
    # If content is very short (< 50 chars) and no code indicators, likely a prompt
    if len(content) < 50 and not any(indicator in content for indicator in code_indicators):
        return False
    
    # Check for multiple code indicators
    indicator_count = sum(1 for indicator in code_indicators if indicator in content)
    
    # If 3+ code indicators present, likely code
    return indicator_count >= 3


async def generate_code_with_gemini(prompt: str) -> str:
    """Generate JavaScript code using Gemini API"""
    if not GEMINI_AVAILABLE:
        raise Exception("Gemini API not available. Set GEMINI_API_KEY environment variable.")
    
    generation_prompt = f"""Generate ONLY JavaScript code for this request: {prompt}

CRITICAL RULES:
- Output ONLY valid JavaScript code
- NO explanations, NO markdown formatting, NO code fences (```), NO "Here's the code" text
- Start directly with JavaScript code
- Add inline comments to explain the code
- Follow best practices and make it production-ready
- Ensure compatibility with Deno runtime

JavaScript code:"""
    
    response = await asyncio.to_thread(
        gemini_client.models.generate_content,
        model="gemini-2.5-flash",
        contents=generation_prompt
    )
    
    generated_code = response.text.strip()
    
    # Clean up markdown code fences if AI ignored instructions
    if "```" in generated_code:
        lines = generated_code.split("\n")
        cleaned_lines = []
        in_code_block = False
        
        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if not line.strip().startswith("Here") and not line.strip().startswith("This"):
                cleaned_lines.append(line)
        
        generated_code = "\n".join(cleaned_lines).strip()
    
    return generated_code


async def verify_code_with_gemini(code: str) -> dict:
    """Verify if content is valid JavaScript code using Gemini"""
    if not GEMINI_AVAILABLE:
        return {"is_valid": True, "message": "Gemini not available, skipping verification"}
    
    verification_prompt = f"""Analyze this content and determine:
1. Is this valid JavaScript code? (yes/no)
2. If yes, provide a brief summary (one line)
3. If no, explain why

Content:
{code}

Respond in this EXACT format:
VALID: yes/no
SUMMARY: your summary here
"""
    
    response = await asyncio.to_thread(
        gemini_client.models.generate_content,
        model="gemini-2.5-flash",
        contents=verification_prompt
    )
    
    result = response.text.strip()
    
    is_valid = "VALID: yes" in result.lower()
    summary_line = [line for line in result.split("\n") if "SUMMARY:" in line]
    summary = summary_line[0].replace("SUMMARY:", "").strip() if summary_line else "Code verified"
    
    return {"is_valid": is_valid, "summary": summary}


async def analyze_code_with_gemini(filename: str, code: str) -> str:
    """Analyze JavaScript code and provide summary and flow"""
    if not GEMINI_AVAILABLE:
        return "Gemini API not available for analysis."
    
    analysis_prompt = f"""Analyze this JavaScript file and provide:

**SUMMARY** (2-3 sentences): What does this code do?

**EXECUTION FLOW** (step-by-step):
- List the main execution steps
- Explain the logic flow

**KEY COMPONENTS**:
- Main functions/classes
- Important variables
- External dependencies

**CODE QUALITY**:
- Potential issues or bugs
- Security concerns
- Suggested improvements

JavaScript Code from '{filename}':
```javascript
{code}
```

Provide clear, concise analysis:"""
    
    response = await asyncio.to_thread(
        gemini_client.models.generate_content,
        model="gemini-2.5-flash",
        contents=analysis_prompt
    )
    
    return response.text.strip()


@mcp.tool()
def create_js_file(filename: str) -> str:
    """Create a new (empty) JavaScript file
    
    Behavior:
    - Only creates the file if it does not exist
    - Does NOT write any content
    - Returns a simple status message
    
    Args:
        filename: Name of the JavaScript file (e.g., 'script.js')
    
    Returns:
        - "✓ Successfully created '<filename>'" if created
        - "Error: File '<filename>' already exists" if it exists
    """
    try:
        path = resolve_path(filename)
        
        if path.exists():
            return f"Error: File '{filename}' already exists"
        
        path.parent.mkdir(parents=True, exist_ok=True)
        # Create empty file
        path.write_text("", encoding="utf-8")
        
        return f"✓ Successfully created '{filename}'"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
async def read_js_file(filename: str) -> str:
    """Read a JavaScript file and provide content with AI-powered analysis
    
    If Gemini API is available, provides:
    - Full file contents
    - Summary of what the code does
    - Execution flow breakdown
    - Key components and suggestions
    
    Args:
        filename: Name of the JavaScript file to read
    
    Returns:
        File contents and AI analysis (if available)
    """
    try:
        path = resolve_path(filename)
        
        if not path.exists():
            return f"Error: File '{filename}' does not exist"
        
        content = path.read_text(encoding="utf-8")
        
        output = [
            f"📄 File: {filename}",
            "=" * 70,
            "",
            "📝 CONTENTS:",
            content,
            "",
            "=" * 70
        ]
        
        # Add AI analysis if Gemini is available
        if GEMINI_AVAILABLE:
            try:
                analysis = await analyze_code_with_gemini(filename, content)
                output.extend([
                    "",
                    "🤖 AI ANALYSIS:",
                    "",
                    analysis
                ])
            except Exception as e:
                output.extend([
                    "",
                    f"⚠️  AI analysis unavailable: {str(e)}"
                ])
        else:
            output.extend([
                "",
                "💡 Tip: Set GEMINI_API_KEY environment variable to enable AI analysis"
            ])
        
        return "\n".join(output)
        
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
async def write_js_file(filename: str, content: str) -> str:
    """Write to a JavaScript file with intelligent content handling
    
    Smart behavior:
    - If content looks like a PROMPT (short text, no code): Uses Gemini to generate code
    - If content looks like CODE: Verifies with Gemini and writes directly
    
    Args:
        filename: Name of the JavaScript file
        content: Either JavaScript code OR a prompt describing what to generate
    
    Returns:
        Success message with verification/generation details
    """
    try:
        path = resolve_path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Determine if content is code or a prompt
        is_code = is_code_content(content)
        
        if is_code:
            # Content appears to be code - verify and write
            if GEMINI_AVAILABLE:
                verification = await verify_code_with_gemini(content)
                if verification["is_valid"]:
                    path.write_text(content, encoding="utf-8")
                    return f"✓ Successfully wrote to '{filename}'\n\n🤖 Gemini Verification: {verification['summary']}"
                else:
                    # Still write it, but warn user
                    path.write_text(content, encoding="utf-8")
                    return f"⚠️  Wrote to '{filename}' but Gemini detected potential issues:\n{verification['summary']}"
            else:
                # No Gemini available, just write
                path.write_text(content, encoding="utf-8")
                return f"✓ Successfully wrote to '{filename}'"
        
        else:
            # Content appears to be a prompt - generate code
            if not GEMINI_AVAILABLE:
                return (
                    "Error: Content looks like a prompt, but Gemini API is not available.\n"
                    "Set GEMINI_API_KEY to enable code generation, or provide actual JavaScript code."
                )
            
            generated_code = await generate_code_with_gemini(content)
            path.write_text(generated_code, encoding="utf-8")
            
            return f"""✓ Successfully generated and wrote to '{filename}'

🤖 AI Generated Code from prompt: "{content[:100]}..."

📝 Generated Code:
{generated_code}"""
        
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
async def execute_js_file(filename: str, args: Optional[list[str]] = None) -> str:
    """Execute a JavaScript file using Deno
    
    Args:
        filename: Name of the JavaScript file to execute
        args: Optional command-line arguments to pass to the script
    
    Returns:
        Execution output (stdout, stderr, exit code)
    """
    if args is None:
        args = []
    
    try:
        path = resolve_path(filename)
        
        if not path.exists():
            return f"Error: File '{filename}' does not exist"
        
        # Check if Deno is available
        try:
            check_result = await asyncio.create_subprocess_exec(
                "deno", "--version",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            await check_result.communicate()
            
            if check_result.returncode != 0:
                return "Error: Deno is not installed or not in PATH"
        except FileNotFoundError:
            return "Error: Deno is not installed or not in PATH"
        
        # Execute the JavaScript file with Deno
        cmd = ["deno", "run", "--allow-all", str(path)] + args
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(BASE_DIR)
        )
        
        stdout, stderr = await process.communicate()
        
        output_parts = []
        output_parts.append(f"🚀 Executed '{filename}' with Deno\n")
        output_parts.append("=" * 50)
        
        if stdout:
            output_parts.append(f"\n📤 STDOUT:\n{stdout.decode('utf-8')}")
        
        if stderr:
            output_parts.append(f"\n⚠️  STDERR:\n{stderr.decode('utf-8')}")
        
        output_parts.append(f"\n🔢 Exit code: {process.returncode}")
        
        if process.returncode == 0:
            output_parts.append("✓ Execution completed successfully")
        else:
            output_parts.append("✗ Execution failed")
        
        return "\n".join(output_parts)
        
    except Exception as e:
        return f"Error executing file: {str(e)}"


@mcp.tool()
def list_js_files() -> str:
    """List all JavaScript files in the working directory
    
    Returns:
        List of JavaScript files
    """
    try:
        js_files = list(BASE_DIR.rglob("*.js"))
        
        if not js_files:
            return "No JavaScript files found in the directory"
        
        files_list = [str(f.relative_to(BASE_DIR)) for f in js_files]
        files_list.sort()
        
        return f"📁 JavaScript files ({len(files_list)}):\n" + "\n".join(f"  • {f}" for f in files_list)
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def delete_js_file(filename: str) -> str:
    """Delete a JavaScript file
    
    Args:
        filename: Name of the JavaScript file to delete
    
    Returns:
        Success or error message
    """
    try:
        path = resolve_path(filename)
        
        if not path.exists():
            return f"Error: File '{filename}' does not exist"
        
        path.unlink()
        return f"✓ Successfully deleted '{filename}'"
    except Exception as e:
        return f"Error: {str(e)}"


async def interactive_menu() -> None:
    """Option-driven CLI loop for managing JavaScript files."""
    MENU = """
========== JavaScript File MCP Utility ==========
1) Create empty JS file
2) Read JS file (with optional AI analysis)
3) Write JS file (code or prompt)
4) Execute JS file with Deno
5) List all JS files
6) Delete JS file
7) Run MCP server (for MCP-compatible clients)
0) Exit
==================================================
"""
    while True:
        print(MENU)
        choice = input("Select an option: ").strip()

        if choice == "0":
            print("👋 Exiting. Goodbye!")
            break

        elif choice == "1":
            # Create empty JS file
            filename = input("Enter filename to create (e.g., script.js): ").strip()
            result = create_js_file(filename)
            print(result)

        elif choice == "2":
            # Read JS file
            print(list_js_files())
            filename = input("Enter filename to read: ").strip()
            result = await read_js_file(filename)
            print(result)

        elif choice == "3":
            # Write JS file (code or prompt)
            print(list_js_files())
            filename = input("Enter filename to write (will be created if not exists): ").strip()
            print("Enter content (JS code OR prompt; end with a single line containing only 'EOF'):")
            lines = []
            while True:
                line = input()
                if line.strip() == "EOF":
                    break
                lines.append(line)
            content = "\n".join(lines)
            result = await write_js_file(filename, content)
            print(result)

        elif choice == "4":
            # Execute JS file with Deno
            print(list_js_files())
            filename = input("Enter filename to execute: ").strip()
            args_line = input("Enter arguments (space-separated, or leave empty): ").strip()
            args = args_line.split() if args_line else []
            result = await execute_js_file(filename, args=args)
            print(result)

        elif choice == "5":
            # List JS files
            print(list_js_files())

        elif choice == "6":
            # Delete JS file
            print(list_js_files())
            filename = input("Enter filename to delete: ").strip()
            result = delete_js_file(filename)
            print(result)

        elif choice == "7":
            # Run MCP server
            print("🚀 Starting MCP server (press Ctrl+C to stop)...")
            mcp.run()

        else:
            print("❌ Invalid choice. Please select a valid option.")



if __name__ == "__main__":
    try:
        # asyncio.run(interactive_menu())
        mcp.run()
    except KeyboardInterrupt:
        print("\n👋 Exiting due to keyboard interrupt.")
