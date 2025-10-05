"""
Chat Persistence Service - Handle saving and loading chat history from database
"""

import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class ChatPersistenceService:
    """Service for persisting chat sessions and messages to database."""

    def __init__(
        self,
        backend: str = "sqlite",
        connection_string: str = "pantry.db",
        user_id: Optional[int] = None,
    ):
        """
        Initialize chat persistence service.

        Args:
            backend: Database backend ('sqlite' or 'postgresql')
            connection_string: Database connection string or file path
            user_id: User ID for multi-user mode (None for single-user SQLite)
        """
        self.backend = backend.lower()
        self.connection_string = connection_string
        self.user_id = user_id

    def _get_connection(self):
        """Get database connection."""
        if self.backend == "postgresql":
            return psycopg2.connect(
                self.connection_string, cursor_factory=RealDictCursor
            )
        return sqlite3.connect(self.connection_string)

    def save_session(
        self,
        session_id: str,
        model: str = "anthropic/claude-3.5-sonnet",
        message_count: int = 0,
    ) -> bool:
        """
        Save or update a chat session.

        Args:
            session_id: Unique session identifier
            model: LLM model used
            message_count: Current message count

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()

                if self.backend == "postgresql":
                    if self.user_id:
                        cursor.execute(
                            """
INSERT INTO chat_sessions (id, user_id, created_at, last_activity, model, message_count)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (id) DO UPDATE SET
last_activity = EXCLUDED.last_activity,
model = EXCLUDED.model,
message_count = EXCLUDED.message_count""",
                            (session_id, self.user_id, now, now, model, message_count),
                        )
                    else:
                        cursor.execute(
                            """
INSERT INTO chat_sessions (id, created_at, last_activity, model, message_count)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (id) DO UPDATE SET
last_activity = EXCLUDED.last_activity,
model = EXCLUDED.model,
message_count = EXCLUDED.message_count""",
                            (session_id, now, now, model, message_count),
                        )
                else:
                    # SQLite - single user mode only
                    cursor.execute(
                        """
INSERT OR REPLACE INTO ChatSessions (id, created_at, last_activity, model, message_count)
VALUES (?, ?, ?, ?, ?)""",
                        (session_id, now, now, model, message_count),
                    )

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to save chat session {session_id}: {e}")
            return False

    def save_message(
        self,
        session_id: str,
        role: str,
        content: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        sequence: int = 0,
    ) -> bool:
        """
        Save a chat message.

        Args:
            session_id: Session ID this message belongs to
            role: Message role ('user', 'assistant', 'tool')
            content: Message content (can be None for tool calls)
            tool_calls: Tool calls data (for assistant messages)
            tool_call_id: Tool call ID (for tool result messages)
            tool_name: Tool name (for tool result messages)
            sequence: Message sequence number within the session

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure session exists before saving message
            session_info = self.get_session_info(session_id)
            if not session_info.get("exists"):
                logger.warning(f"Session {session_id} doesn't exist, creating it now")
                self.save_session(session_id)

            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()

                # Serialize tool_calls to JSON if present
                tool_calls_json = json.dumps(tool_calls) if tool_calls else None

                if self.backend == "postgresql":
                    cursor.execute(
                        """
INSERT INTO chat_messages
(session_id, role, content, tool_calls, tool_call_id, tool_name, timestamp, sequence)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            session_id,
                            role,
                            content,
                            tool_calls_json,
                            tool_call_id,
                            tool_name,
                            now,
                            sequence,
                        ),
                    )
                else:
                    cursor.execute(
                        """
INSERT INTO ChatMessages
(session_id, role, content, tool_calls, tool_call_id, tool_name, timestamp, sequence)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            session_id,
                            role,
                            content,
                            tool_calls_json,
                            tool_call_id,
                            tool_name,
                            now,
                            sequence,
                        ),
                    )

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to save message for session {session_id}: {e}")
            return False

    def load_session_messages(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Load messages for a chat session.

        Args:
            session_id: Session ID to load messages for
            limit: Maximum number of messages to load (None for all)

        Returns:
            List of messages in conversation format
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Build query with optional limit
                if self.backend == "postgresql":
                    query = """
SELECT role, content, tool_calls, tool_call_id, tool_name, sequence
FROM chat_messages
WHERE session_id = %s
ORDER BY sequence ASC"""
                    params = [session_id]
                else:
                    query = """
SELECT role, content, tool_calls, tool_call_id, tool_name, sequence
FROM ChatMessages
WHERE session_id = ?
ORDER BY sequence ASC"""
                    params = [session_id]

                if limit:
                    query += f" LIMIT {limit}"

                cursor.execute(query, params)
                rows = cursor.fetchall()

                messages = []
                for row in rows:
                    if self.backend == "postgresql":
                        # RealDictCursor returns dictionaries
                        role = row["role"]
                        content = row["content"]
                        tool_calls_json = row["tool_calls"]
                        tool_call_id = row["tool_call_id"]
                        tool_name = row["tool_name"]
                    else:
                        # SQLite returns tuples
                        (
                            role,
                            content,
                            tool_calls_json,
                            tool_call_id,
                            tool_name,
                            _,
                        ) = row

                    message = {"role": role}

                    # For tool messages, content is required even if empty
                    if role == "tool":
                        message["content"] = content or ""
                    elif content:
                        message["content"] = content

                    if tool_calls_json:
                        try:
                            message["tool_calls"] = json.loads(tool_calls_json)
                        except json.JSONDecodeError:
                            logger.warning(
                                f"Failed to parse tool_calls JSON for session {session_id}"
                            )

                    if tool_call_id:
                        message["tool_call_id"] = tool_call_id

                    if tool_name:
                        message["name"] = tool_name

                    messages.append(message)

                return messages

        except Exception as e:
            logger.error(f"Failed to load messages for session {session_id}: {e}")
            return []

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a chat session.

        Args:
            session_id: Session ID to get info for

        Returns:
            Session info dict or None if not found
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if self.backend == "postgresql":
                    query = """
SELECT created_at, last_activity, model, message_count
FROM chat_sessions
WHERE id = %s"""
                    if self.user_id:
                        query += " AND user_id = %s"
                        cursor.execute(query, (session_id, self.user_id))
                    else:
                        cursor.execute(query, (session_id,))
                else:
                    cursor.execute(
                        """
SELECT created_at, last_activity, model, message_count
FROM ChatSessions
WHERE id = ?""",
                        (session_id,),
                    )

                row = cursor.fetchone()
                if row:
                    if self.backend == "postgresql":
                        # RealDictCursor returns dictionaries
                        created_at = row["created_at"]
                        last_activity = row["last_activity"]
                        model = row["model"]
                        message_count = row["message_count"]
                    else:
                        # SQLite returns tuples
                        created_at, last_activity, model, message_count = row

                    # Convert datetime objects to ISO format strings
                    if hasattr(created_at, "isoformat"):
                        created_at = created_at.isoformat()
                    if hasattr(last_activity, "isoformat"):
                        last_activity = last_activity.isoformat()

                    return {
                        "exists": True,
                        "session_id": session_id,
                        "created_at": created_at,
                        "last_activity": last_activity,
                        "model": model,
                        "message_count": message_count,
                    }
                return {"exists": False}

        except Exception as e:
            logger.error(f"Failed to get session info for {session_id}: {e}")
            return {"exists": False}

    def clear_session(self, session_id: str) -> bool:
        """
        Clear all messages from a session but keep the session record.

        Args:
            session_id: Session ID to clear

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if self.backend == "postgresql":
                    # Delete messages
                    cursor.execute(
                        "DELETE FROM chat_messages WHERE session_id = %s", (session_id,)
                    )
                    # Reset message count
                    cursor.execute(
                        """
UPDATE chat_sessions
SET message_count = 0, last_activity = %s
WHERE id = %s""",
                        (datetime.now().isoformat(), session_id),
                    )
                else:
                    # Delete messages
                    cursor.execute(
                        "DELETE FROM ChatMessages WHERE session_id = ?", (session_id,)
                    )
                    # Reset message count
                    cursor.execute(
                        """
UPDATE ChatSessions
SET message_count = 0, last_activity = ?
WHERE id = ?""",
                        (datetime.now().isoformat(), session_id),
                    )

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to clear session {session_id}: {e}")
            return False

    def cleanup_old_sessions(
        self, max_age_hours: int = 168
    ) -> int:  # 168 hours = 7 days
        """
        Clean up old inactive sessions.

        Args:
            max_age_hours: Maximum age in hours for sessions to keep

        Returns:
            int: Number of sessions cleaned up
        """
        try:
            cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
            cutoff_iso = datetime.fromtimestamp(cutoff_time).isoformat()

            with self._get_connection() as conn:
                cursor = conn.cursor()

                if self.backend == "postgresql":
                    # Count sessions to be deleted
                    cursor.execute(
                        """
SELECT COUNT(*) FROM chat_sessions
WHERE last_activity < %s""",
                        (cutoff_iso,),
                    )
                    count = cursor.fetchone()[0]

                    # Delete old sessions (messages will be deleted by CASCADE)
                    cursor.execute(
                        """
DELETE FROM chat_sessions
WHERE last_activity < %s""",
                        (cutoff_iso,),
                    )
                else:
                    # Count sessions to be deleted
                    cursor.execute(
                        """
SELECT COUNT(*) FROM ChatSessions
WHERE last_activity < ?""",
                        (cutoff_iso,),
                    )
                    count = cursor.fetchone()[0]

                    # Delete old sessions (messages will be deleted by CASCADE)
                    cursor.execute(
                        """
DELETE FROM ChatSessions
WHERE last_activity < ?""",
                        (cutoff_iso,),
                    )

                conn.commit()
                logger.info(f"Cleaned up {count} old chat sessions")
                return count

        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")
            return 0


def get_chat_persistence_service(
    user_id: Optional[int] = None,
) -> ChatPersistenceService:
    """
    Factory function to create chat persistence service based on environment.

    Args:
        user_id: User ID for multi-user mode (None for single-user SQLite)

    Returns:
        ChatPersistenceService instance
    """
    backend = os.getenv("PANTRY_BACKEND", "sqlite").lower()

    if backend == "postgresql":
        connection_string = os.getenv("PANTRY_DATABASE_URL")
        if not connection_string:
            raise ValueError("PANTRY_DATABASE_URL must be set for PostgreSQL backend")
        return ChatPersistenceService(backend, connection_string, user_id)
    db_path = os.getenv("PANTRY_DB_PATH", "pantry.db")
    return ChatPersistenceService("sqlite", db_path, None)
