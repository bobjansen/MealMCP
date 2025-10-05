#!/usr/bin/env python3
"""
OpenRouter CLI - Refactored to use shared service layer

This CLI app uses the shared OpenRouterService for LLM integration.
"""

import os
import sys
from pathlib import Path
import argparse
import logging
import uuid

# Add parent directory to path so we can import from main package
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.status import Status
from rich.table import Table

from openrouter_service import get_openrouter_service, is_openrouter_available
from mcp_tools import MCP_TOOLS

# Set up logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

console = Console()


class OpenRouterCLI:
    """CLI interface using shared OpenRouter service."""

    def __init__(self, api_key: str, model: str = "anthropic/claude-3.5-sonnet"):
        self.service = get_openrouter_service(api_key)
        if not self.service:
            raise RuntimeError("Failed to initialize OpenRouter service")

        self.model = model
        self.session_id = str(uuid.uuid4())  # Unique session for CLI
        self.user_id = None  # For multi-user mode

    def chat_loop(self):
        """Main chat loop."""
        console.print(
            Panel(
                "[bold green]MealMCP CLI[/bold green] (Refactored)\n"
                f"Model: {self.model}\n"
                f"Available tools: {len(self.service.openai_tools)}\n"
                f"Session ID: {self.session_id[:8]}...\n"
                "Type 'quit', 'exit', or 'q' to end the conversation.\n"
                "Type '/help' for available commands.",
                title="Welcome",
            )
        )

        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold blue]You[/bold blue]")

                if user_input.lower() in ["quit", "exit", "q"]:
                    console.print("[yellow]Goodbye![/yellow]")
                    break

                if user_input.startswith("/"):
                    self._handle_command(user_input)
                    continue

                # Process message through service
                with Status("[dim]Thinking...[/dim]"):
                    result = self.service.chat(
                        message=user_input,
                        session_id=self.session_id,
                        model=self.model,
                        user_id=self.user_id,
                    )

                # Display responses
                self._display_chat_result(result)

            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted by user[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                logger.error(f"Chat loop error: {e}")

    def _display_chat_result(self, result: dict):
        """Display the chat result with responses and tool calls."""
        responses = result.get("responses", [])

        for response in responses:
            # Show assistant content
            content = response.get("content", "")
            if content:
                console.print(f"\n[bold green]Assistant[/bold green]: {content}")

            # Show tool calls if any
            tool_calls = response.get("tool_calls", [])
            for tool_result in tool_calls:
                tool_name = tool_result["tool_name"]
                console.print(f"[blue]🔧 Executed tool:[/blue] {tool_name}")

        # Show summary info
        iterations = result.get("total_iterations", 1)
        if iterations > 1:
            console.print(f"[dim]Completed in {iterations} iterations[/dim]")

    def _handle_command(self, command: str):
        """Handle CLI commands."""
        command = command.lower().strip()

        if command == "/help":
            self._show_help()
        elif command == "/models":
            self._show_models()
        elif command == "/tools":
            self._show_tools()
        elif command == "/reset":
            self.service.reset_session(self.session_id)
            console.print("[green]Conversation reset[/green]")
        elif command == "/session":
            self._show_session_info()
        elif command.startswith("/model "):
            model_name = command.split(" ", 1)[1]
            self.model = model_name
            console.print(f"[green]Model set to: {model_name}[/green]")
        else:
            console.print(f"[red]Unknown command: {command}[/red]")

    def _show_help(self):
        """Show available commands."""
        help_table = Table(title="Available Commands")
        help_table.add_column("Command", style="cyan")
        help_table.add_column("Description", style="white")

        help_table.add_row("/help", "Show this help message")
        help_table.add_row("/models", "List available models")
        help_table.add_row("/tools", "List available MCP tools")
        help_table.add_row("/reset", "Reset conversation history")
        help_table.add_row("/session", "Show session information")
        help_table.add_row("/model <name>", "Change the current model")
        help_table.add_row("quit/exit/q", "Exit the CLI")

        console.print(help_table)

    def _show_models(self):
        """Show available OpenRouter models."""
        with Status("[dim]Fetching models...[/dim]"):
            models = self.service.get_models()

        if not models:
            console.print("[red]Failed to fetch models[/red]")
            return

        # Show popular models for meal planning
        popular_models = [
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3-haiku",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "meta-llama/llama-3.1-8b-instruct",
            "google/gemini-pro",
        ]

        model_table = Table(title="Popular Models for Meal Planning")
        model_table.add_column("Model", style="cyan")
        model_table.add_column("Provider", style="green")
        model_table.add_column("Context", style="yellow")

        for model_data in models:
            if model_data["id"] in popular_models:
                model_table.add_row(
                    model_data["id"],
                    model_data.get("name", ""),
                    f"{model_data.get('context_length', 'Unknown'):,}",
                )

        console.print(model_table)
        console.print(f"[dim]Current model: {self.model}[/dim]")
        console.print(f"[dim]Total available models: {len(models)}[/dim]")

    def _show_tools(self):
        """Show available MCP tools."""
        tools = self.service.get_available_tools()

        tool_table = Table(title="Available MCP Tools")
        tool_table.add_column("Tool Name", style="cyan")
        tool_table.add_column("Description", style="white")

        for tool in tools[:10]:  # Show first 10 tools
            tool_table.add_row(tool["name"], tool["description"][:80] + "...")

        console.print(tool_table)
        console.print(f"[dim]Showing 10 of {len(tools)} available tools[/dim]")

    def _show_session_info(self):
        """Show session information."""
        info = self.service.get_session_info(self.session_id)

        if not info.get("exists"):
            console.print("[yellow]No active session[/yellow]")
            return

        session_table = Table(title="Session Information")
        session_table.add_column("Property", style="cyan")
        session_table.add_column("Value", style="white")

        session_table.add_row(
            "Session ID", info.get("session_id", "Unknown")[:16] + "..."
        )
        session_table.add_row("Messages", str(info.get("message_count", 0)))
        session_table.add_row("Created", info.get("created_at", "Unknown"))
        session_table.add_row("Last Activity", info.get("last_activity", "Unknown"))

        console.print(session_table)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="MealMCP OpenRouter CLI (Refactored)")
    parser.add_argument(
        "--api-key", help="OpenRouter API key (or set OPENROUTER_API_KEY env var)"
    )
    parser.add_argument(
        "--model", default="anthropic/claude-3.5-sonnet", help="Model to use"
    )
    parser.add_argument(
        "--backend", choices=["sqlite", "postgresql"], help="Database backend"
    )
    parser.add_argument("--db-url", help="Database connection URL for PostgreSQL")

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        console.print("[red]Error: OpenRouter API key required.[/red]")
        console.print("Set OPENROUTER_API_KEY environment variable or use --api-key")
        sys.exit(1)

    # Set environment variables if provided
    if args.backend:
        os.environ["PANTRY_BACKEND"] = args.backend
    if args.db_url:
        os.environ["PANTRY_DATABASE_URL"] = args.db_url

    try:
        # Initialize and start CLI
        cli = OpenRouterCLI(api_key, args.model)
        cli.chat_loop()

    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
