"""
OpenRouter Service - Shared LLM integration for CLI and Flask
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import requests

from mcp_tools import MCP_TOOLS
from mcp_tool_router import MCPToolRouter
from pantry_manager_factory import PantryManagerFactory
from web_auth_simple import WebUserManager
from chat_persistence import ChatPersistenceService, get_chat_persistence_service

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """OpenRouter API client with function calling support."""

    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/MealMCP/openrouter-service",
                "X-Title": "MealMCP OpenRouter Service",
            }
        )

    def get_models(self) -> List[Dict[str, Any]]:
        """Get available models from OpenRouter."""
        try:
            response = self.session.get(f"{self.base_url}/models")
            response.raise_for_status()
            return response.json().get("data", [])
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            return []

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """Send chat completion request with optional tool calling."""

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        try:
            logger.debug(
                f"Sending chat completion request with {len(messages)} messages"
            )
            response = self.session.post(
                f"{self.base_url}/chat/completions", json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"Chat completion failed: {e}")
            logger.error(
                f"Response content: {e.response.text if e.response else 'N/A'}"
            )
            logger.error(f"Payload messages: {json.dumps(messages, indent=2)}")
            raise


class MCPToolConverter:
    """Converts MCP tool definitions to OpenAI function calling format."""

    @staticmethod
    def convert_mcp_tools_to_openai(
        mcp_tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert MCP tool definitions to OpenAI function calling format."""
        openai_tools = []

        for tool in mcp_tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["inputSchema"],
                },
            }
            openai_tools.append(openai_tool)

        return openai_tools


class ConversationSession:
    """Manages a single conversation session with persistence support."""

    def __init__(
        self,
        session_id: str,
        persistence_service: Optional[ChatPersistenceService] = None,
    ):
        self.session_id = session_id
        self.messages: List[Dict[str, Any]] = []
        self.tool_call_count = 0
        self.max_tool_calls = 10
        self.created_at = None
        self.last_activity = None
        self.sequence_counter = 0
        self.persistence_service = persistence_service

        # Load existing messages if persistence is available
        if self.persistence_service:
            self._load_from_persistence()

    def _load_from_persistence(self):
        """Load session data from persistence service."""
        try:
            # Load messages first
            self.messages = self.persistence_service.load_session_messages(
                self.session_id
            )
            self.sequence_counter = len(self.messages)

            # Load session info if exists, otherwise create session
            session_info = self.persistence_service.get_session_info(self.session_id)
            if session_info.get("exists"):
                self.created_at = session_info.get("created_at")
                self.last_activity = session_info.get("last_activity")
            else:
                # Create session in persistence if messages exist but session doesn't
                if self.messages:
                    from datetime import datetime

                    now = datetime.now()
                    self.created_at = now
                    self.last_activity = now
                    self.persistence_service.save_session(
                        self.session_id,
                        model="anthropic/claude-3.5-sonnet",
                        message_count=len(self.messages),
                    )
        except Exception as e:
            logger.warning(
                f"Failed to load session {self.session_id} from persistence: {e}"
            )

    def _save_to_persistence(self):
        """Save session to persistence service."""
        if not self.persistence_service:
            return

        try:
            # Save/update session info
            self.persistence_service.save_session(
                self.session_id,
                model="anthropic/claude-3.5-sonnet",  # Default model
                message_count=len(self.messages),
            )
        except Exception as e:
            logger.warning(
                f"Failed to save session {self.session_id} to persistence: {e}"
            )

    def add_user_message(self, content: str):
        """Add user message to conversation."""
        message = {"role": "user", "content": content}
        self.messages.append(message)

        # Save to persistence
        if self.persistence_service:
            self.persistence_service.save_message(
                self.session_id, "user", content, sequence=self.sequence_counter
            )
            self.sequence_counter += 1

        self._update_activity()

    def add_assistant_message(
        self, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None
    ):
        """Add assistant message to conversation."""
        message = {"role": "assistant", "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls
        self.messages.append(message)

        # Save to persistence
        if self.persistence_service:
            self.persistence_service.save_message(
                self.session_id,
                "assistant",
                content,
                tool_calls=tool_calls,
                sequence=self.sequence_counter,
            )
            self.sequence_counter += 1

        self._update_activity()

    def add_tool_result(self, tool_call_id: str, tool_name: str, result: str):
        """Add tool execution result to conversation."""
        message = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": result,
        }
        self.messages.append(message)

        # Save to persistence
        if self.persistence_service:
            self.persistence_service.save_message(
                self.session_id,
                "tool",
                result,
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                sequence=self.sequence_counter,
            )
            self.sequence_counter += 1

        self._update_activity()

    def reset(self):
        """Reset conversation history."""
        self.messages.clear()
        self.tool_call_count = 0
        self.sequence_counter = 0

        # Clear from persistence
        if self.persistence_service:
            self.persistence_service.clear_session(self.session_id)

        self._update_activity()

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get current conversation messages."""
        return self.messages.copy()

    def _update_activity(self):
        """Update last activity timestamp."""
        from datetime import datetime

        self.last_activity = datetime.now()
        if not self.created_at:
            self.created_at = self.last_activity


class OpenRouterService:
    """Main service for OpenRouter LLM integration with MCP tools."""

    def __init__(self, api_key: str):
        self.client = OpenRouterClient(api_key)
        self.converter = MCPToolConverter()
        self.tool_router = MCPToolRouter()
        self.sessions: Dict[str, ConversationSession] = {}

        # Convert MCP tools to OpenAI format once
        self.openai_tools = self.converter.convert_mcp_tools_to_openai(MCP_TOOLS)

        # Initialize backend managers
        self._initialize_backend()

        # Initialize persistence service
        self.persistence_service = None
        try:
            self.persistence_service = get_chat_persistence_service()
        except Exception as e:
            logger.warning(f"Chat persistence not available: {e}")

    def _initialize_backend(self):
        """Initialize backend managers."""
        backend = os.getenv("PANTRY_BACKEND", "sqlite")

        if backend.lower() == "postgresql":
            db_url = os.getenv("PANTRY_DATABASE_URL")
            if db_url:
                self.user_manager = WebUserManager(backend, db_url)
                self.pantry_manager = None  # Will be user-specific
            else:
                logger.warning("PostgreSQL backend selected but no PANTRY_DATABASE_URL")
                self.pantry_manager = PantryManagerFactory.from_environment()
                self.user_manager = None
        else:
            # Single-user SQLite mode
            self.pantry_manager = PantryManagerFactory.from_environment()
            self.user_manager = None

    def get_session(
        self, session_id: str, user_id: Optional[int] = None
    ) -> ConversationSession:
        """Get or create a conversation session."""
        if session_id not in self.sessions:
            # Create persistence service for this user if needed
            persistence_service = None
            if self.persistence_service:
                try:
                    if (
                        user_id
                        and os.getenv("PANTRY_BACKEND", "sqlite").lower()
                        == "postgresql"
                    ):
                        persistence_service = get_chat_persistence_service(user_id)
                    else:
                        persistence_service = self.persistence_service
                except Exception as e:
                    logger.warning(
                        f"Failed to create user-specific persistence for user {user_id}: {e}"
                    )

            self.sessions[session_id] = ConversationSession(
                session_id, persistence_service
            )
        return self.sessions[session_id]

    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove old inactive sessions."""
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        old_sessions = [
            sid
            for sid, session in self.sessions.items()
            if session.last_activity and session.last_activity < cutoff
        ]

        for sid in old_sessions:
            del self.sessions[sid]

        logger.info(f"Cleaned up {len(old_sessions)} old sessions")

    def _get_pantry_manager(self, user_id: Optional[int] = None):
        """Get pantry manager for the current user."""
        if self.pantry_manager:
            return self.pantry_manager

        if self.user_manager and user_id:
            # For multi-user mode, create user-specific manager
            from pantry_manager_shared import SharedPantryManager

            db_url = os.getenv("PANTRY_DATABASE_URL")
            return SharedPantryManager(db_url, user_id, "postgresql")

        raise RuntimeError("No pantry manager available")

    def execute_tool(
        self, tool_name: str, arguments: Dict[str, Any], user_id: Optional[int] = None
    ) -> str:
        """Execute an MCP tool and return the result."""
        try:
            pantry_manager = self._get_pantry_manager(user_id)

            # Execute tool through the router
            result = self.tool_router.call_tool(tool_name, arguments, pantry_manager)

            # Truncate large results to avoid API limits
            result = self._truncate_large_results(result, tool_name)

            # Format result as JSON string
            return json.dumps(result, indent=2, default=str)

        except Exception as e:
            error_result = {"error": str(e), "tool": tool_name, "arguments": arguments}
            logger.error(f"Tool execution failed: {e}")
            return json.dumps(error_result, indent=2)

    def _truncate_large_results(
        self, result: Dict[str, Any], tool_name: str
    ) -> Dict[str, Any]:
        """Truncate large results to avoid API message size limits."""
        MAX_CHARS = 8000  # Conservative limit for OpenRouter

        # Check if result has large arrays that should be truncated
        if result.get("status") == "success":
            # Handle recipe lists
            if "recipes" in result and isinstance(result["recipes"], list):
                recipes = result["recipes"]
                if len(recipes) > 20:  # More than 20 recipes
                    result["recipes"] = recipes[:20]
                    result["truncated"] = True
                    result["total_found"] = len(recipes)
                    result["showing"] = 20
                    result["message"] = (
                        f"Showing first 20 of {len(recipes)} results. Use more specific search terms to narrow results."
                    )

            # Handle pantry items
            elif "pantry_items" in result and isinstance(result["pantry_items"], list):
                items = result["pantry_items"]
                if len(items) > 50:  # More than 50 items
                    result["pantry_items"] = items[:50]
                    result["truncated"] = True
                    result["total_found"] = len(items)
                    result["showing"] = 50

            # Handle other large arrays
            for key in ["items", "preferences", "meal_plan"]:
                if (
                    key in result
                    and isinstance(result[key], list)
                    and len(result[key]) > 30
                ):
                    original_length = len(result[key])
                    result[key] = result[key][:30]
                    result["truncated"] = True
                    result["total_found"] = original_length
                    result["showing"] = 30

        # Final size check - if still too large, summarize
        result_str = json.dumps(result, default=str)
        if len(result_str) > MAX_CHARS:
            # Create a summary instead
            summary_result = {
                "status": result.get("status", "success"),
                "message": f"Result too large ({len(result_str)} chars). ",
                "tool_name": tool_name,
                "truncated": True,
            }

            # Add key information based on result type
            if "recipes" in result:
                summary_result[
                    "message"
                ] += f"Found {len(result.get('recipes', []))} recipes. Please use more specific search terms."
                summary_result["recipe_count"] = len(result.get("recipes", []))
            elif "pantry_items" in result:
                summary_result[
                    "message"
                ] += f"Found {len(result.get('pantry_items', []))} pantry items."
                summary_result["item_count"] = len(result.get("pantry_items", []))

            return summary_result

        return result

    def process_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        session: ConversationSession,
        user_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Process and execute tool calls from the assistant."""
        results = []

        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            arguments = json.loads(tool_call["function"]["arguments"])
            tool_call_id = tool_call["id"]

            # Execute the tool
            result = self.execute_tool(tool_name, arguments, user_id)

            # Add result to conversation
            session.add_tool_result(tool_call_id, tool_name, result)

            results.append(
                {"tool_call_id": tool_call_id, "tool_name": tool_name, "result": result}
            )

        return results

    def _build_system_message(self, user_id: Optional[int] = None) -> str:
        """Build system message with user profile context."""
        system_parts = [
            "You are a helpful AI assistant for meal planning and recipe management.",
            "You have access to tools to help users manage their pantry, recipes, meal plans, and preferences.",
        ]

        # Add user profile information if available
        if user_id:
            try:
                pantry_manager = self._get_pantry_manager(user_id)
                household = pantry_manager.get_household_characteristics()
                preferences = pantry_manager.get_preferences()

                # Add household information
                adults = household.get("adults", 2)
                children = household.get("children", 0)
                total_people = adults + children
                system_parts.append(
                    f"\nHousehold: {adults} adults, {children} children (total: {total_people} people)"
                )

                # Add household goals/notes if available
                notes = household.get("notes", "").strip()
                if notes:
                    system_parts.append(f"\nHousehold goals and preferences:\n{notes}")

                # Add dietary preferences summary
                if preferences:
                    allergies = [
                        p["item"] for p in preferences if p.get("category") == "allergy"
                    ]
                    dietary = [
                        p["item"] for p in preferences if p.get("category") == "dietary"
                    ]
                    dislikes = [
                        p["item"] for p in preferences if p.get("category") == "dislike"
                    ]
                    likes = [
                        p["item"] for p in preferences if p.get("category") == "like"
                    ]

                    pref_parts = []
                    if allergies:
                        pref_parts.append(f"- Allergies: {', '.join(allergies)}")
                    if dietary:
                        pref_parts.append(
                            f"- Dietary restrictions: {', '.join(dietary)}"
                        )
                    if dislikes:
                        pref_parts.append(f"- Dislikes: {', '.join(dislikes)}")
                    if likes:
                        pref_parts.append(f"- Likes: {', '.join(likes)}")

                    if pref_parts:
                        system_parts.append(
                            "\nDietary preferences:\n" + "\n".join(pref_parts)
                        )

                system_parts.append(
                    "\nUse this information to provide personalized meal suggestions and recipe recommendations."
                )

            except Exception as e:
                logger.warning(f"Failed to load user profile for system message: {e}")

        return "\n".join(system_parts)

    def chat(
        self,
        message: str,
        session_id: str,
        model: str = "anthropic/claude-3.5-sonnet",
        user_id: Optional[int] = None,
        max_iterations: int = 5,
    ) -> Dict[str, Any]:
        """Process a chat message and return the response with any tool calls."""
        session = self.get_session(session_id, user_id)

        # Add system message at the start of conversation if this is the first message
        if len(session.get_messages()) == 0:
            system_content = self._build_system_message(user_id)
            session.messages.insert(0, {"role": "system", "content": system_content})

        session.add_user_message(message)

        responses = []
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            try:
                # Get LLM response
                response = self.client.chat_completion(
                    messages=session.get_messages(),
                    model=model,
                    tools=self.openai_tools,
                    tool_choice="auto",
                )

                choice = response["choices"][0]
                message_obj = choice["message"]
                finish_reason = choice["finish_reason"]

                # Extract response content and tool calls
                content = message_obj.get("content", "")
                tool_calls = message_obj.get("tool_calls", [])

                # Add assistant message to session
                session.add_assistant_message(content, tool_calls)

                # Record this response
                response_data = {
                    "content": content,
                    "tool_calls": [],
                    "finish_reason": finish_reason,
                    "iteration": iteration,
                }

                # Process tool calls if any
                if tool_calls and finish_reason == "tool_calls":
                    tool_results = self.process_tool_calls(tool_calls, session, user_id)
                    response_data["tool_calls"] = tool_results
                    responses.append(response_data)
                    continue  # Continue for follow-up
                else:
                    responses.append(response_data)
                    break  # No more tool calls, we're done

            except Exception as e:
                logger.error(f"Chat error on iteration {iteration}: {e}")
                responses.append(
                    {
                        "content": f"I encountered an error: {str(e)}",
                        "tool_calls": [],
                        "finish_reason": "error",
                        "iteration": iteration,
                        "error": str(e),
                    }
                )
                break

        return {
            "session_id": session_id,
            "responses": responses,
            "total_iterations": iteration,
            "message_count": len(session.messages),
            "model": model,
        }

    def get_models(self) -> List[Dict[str, Any]]:
        """Get available OpenRouter models."""
        return self.client.get_models()

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available MCP tools."""
        return MCP_TOOLS

    def reset_session(self, session_id: str):
        """Reset a conversation session."""
        if session_id in self.sessions:
            self.sessions[session_id].reset()

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a session."""
        if session_id not in self.sessions:
            return {"exists": False}

        session = self.sessions[session_id]

        # Handle both datetime objects and ISO strings
        created_at = session.created_at
        if created_at:
            created_at = (
                created_at.isoformat()
                if hasattr(created_at, "isoformat")
                else created_at
            )

        last_activity = session.last_activity
        if last_activity:
            last_activity = (
                last_activity.isoformat()
                if hasattr(last_activity, "isoformat")
                else last_activity
            )

        return {
            "exists": True,
            "session_id": session_id,
            "message_count": len(session.messages),
            "created_at": created_at,
            "last_activity": last_activity,
        }


# Global service instance (will be initialized when API key is available)
_service_instance: Optional[OpenRouterService] = None


def get_openrouter_service(
    api_key: Optional[str] = None,
) -> Optional[OpenRouterService]:
    """Get or create the global OpenRouter service instance."""
    global _service_instance

    if not api_key:
        api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        return None

    if _service_instance is None:
        _service_instance = OpenRouterService(api_key)

    return _service_instance


def is_openrouter_available() -> bool:
    """Check if OpenRouter is available (API key is set)."""
    return bool(os.getenv("OPENROUTER_API_KEY"))
