"""
Flask OpenRouter Integration - Add LLM chat functionality to the web interface
"""

import json
import uuid
import logging
from flask import jsonify, request, session, render_template, render_template_string
from openrouter_service import get_openrouter_service, is_openrouter_available


logger = logging.getLogger(__name__)


def add_openrouter_routes(app, requires_auth_decorator):
    """Add OpenRouter routes to the Flask app."""

    @app.route("/api/chat", methods=["POST"])
    @requires_auth_decorator
    def api_chat():
        """API endpoint for chat messages."""
        try:
            if not is_openrouter_available():
                return (
                    jsonify(
                        {
                            "error": "OpenRouter service not available. Set OPENROUTER_API_KEY environment variable."
                        }
                    ),
                    503,
                )

            data = request.get_json()
            if not data or "message" not in data:
                return jsonify({"error": "Message is required"}), 400

            message = data["message"]
            model = "deepseek/deepseek-chat-v3-0324"

            # Get user ID and create session ID based on user
            backend = app.config.get("PANTRY_BACKEND", "sqlite")
            if backend == "postgresql" and "user_id" in session:
                user_id = session["user_id"]
                session_id = f"user_{user_id}"
            else:
                # Single user mode - use fixed session
                user_id = None
                session_id = "single_user"

            # Get OpenRouter service
            service = get_openrouter_service()
            if not service:
                return (
                    jsonify({"error": "Failed to initialize OpenRouter service"}),
                    500,
                )

            # Process chat message
            result = service.chat(
                message=message, session_id=session_id, model=model, user_id=user_id
            )

            return jsonify(result)

        except Exception as e:
            logger.error(f"Chat API error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/chat/reset", methods=["POST"])
    @requires_auth_decorator
    def api_chat_reset():
        """Reset chat session."""
        try:
            service = get_openrouter_service()
            if not service:
                return jsonify({"error": "OpenRouter service not available"}), 503

            # Get session ID based on user
            backend = app.config.get("PANTRY_BACKEND", "sqlite")
            if backend == "postgresql" and "user_id" in session:
                session_id = f"user_{session['user_id']}"
            else:
                session_id = "single_user"

            service.reset_session(session_id)
            return jsonify({"success": True})

        except Exception as e:
            logger.error(f"Chat reset error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/chat/models")
    @requires_auth_decorator
    def api_chat_models():
        """Get available models."""
        try:
            service = get_openrouter_service()
            if not service:
                return jsonify({"error": "OpenRouter service not available"}), 503

            models = service.get_models()

            # Filter to popular models for meal planning
            popular_models = [
                "anthropic/claude-3.5-sonnet",
                "anthropic/claude-3-haiku",
                "openai/gpt-4o",
                "openai/gpt-4o-mini",
                "meta-llama/llama-3.1-8b-instruct",
                "google/gemini-pro",
            ]

            filtered_models = [
                model for model in models if model["id"] in popular_models
            ]

            return jsonify({"models": filtered_models})

        except Exception as e:
            logger.error(f"Models API error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/chat/session")
    @requires_auth_decorator
    def api_chat_session():
        """Get session information."""
        try:
            service = get_openrouter_service()
            if not service:
                return jsonify({"error": "OpenRouter service not available"}), 503

            # Get session ID based on user
            backend = app.config.get("PANTRY_BACKEND", "sqlite")
            if backend == "postgresql" and "user_id" in session:
                session_id = f"user_{session['user_id']}"
            else:
                session_id = "single_user"

            info = service.get_session_info(session_id)
            return jsonify(info)

        except Exception as e:
            logger.error(f"Session info error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/chat/history")
    @requires_auth_decorator
    def api_chat_history():
        """Get chat history for current session."""
        try:
            service = get_openrouter_service()
            if not service:
                return jsonify({"error": "OpenRouter service not available"}), 503

            # Get session ID and user ID based on backend
            backend = app.config.get("PANTRY_BACKEND", "sqlite")
            if backend == "postgresql" and "user_id" in session:
                user_id = session["user_id"]
                session_id = f"user_{user_id}"
            else:
                user_id = None
                session_id = "single_user"

            # Get session (which will load messages from persistence)
            chat_session = service.get_session(session_id, user_id)
            messages = chat_session.get_messages()

            # Filter messages for frontend display (only user and assistant messages)
            display_messages = []
            for msg in messages:
                if msg["role"] in ["user", "assistant"]:
                    display_messages.append(
                        {
                            "role": msg["role"],
                            "content": msg.get("content", ""),
                            "tool_calls": msg.get("tool_calls", []),
                        }
                    )

            return jsonify({"messages": display_messages})

        except Exception as e:
            logger.error(f"Chat history error: {e}")
            return jsonify({"error": str(e)}), 500
