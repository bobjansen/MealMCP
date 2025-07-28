from typing import Optional, Dict, Any
from contextvars import ContextVar
from pantry_manager import PantryManager
from user_manager import UserManager
import os

# Context variable to store current user
current_user: ContextVar[Optional[str]] = ContextVar('current_user', default=None)

class MCPContext:
    """Manages MCP server context including user authentication and pantry managers."""
    
    def __init__(self):
        self.mode = os.getenv("MCP_MODE", "local")  # "local" or "remote"
        self.user_manager = UserManager(self.mode)
        self.pantry_managers: Dict[str, PantryManager] = {}
        
        # Initialize local user in local mode
        if self.mode == "local":
            local_user = "local_user"
            db_path = self.user_manager.get_user_db_path(local_user)
            self.pantry_managers[local_user] = PantryManager(db_path)
            
            # Initialize database if it doesn't exist
            from db_setup import setup_database
            setup_database(db_path)
    
    def authenticate_and_get_pantry(self, token: Optional[str] = None) -> tuple[Optional[str], Optional[PantryManager]]:
        """Authenticate user and return their PantryManager instance."""
        if self.mode == "local":
            user_id = "local_user"
            if user_id not in self.pantry_managers:
                db_path = self.user_manager.get_user_db_path(user_id)
                self.pantry_managers[user_id] = PantryManager(db_path)
            return user_id, self.pantry_managers[user_id]
        
        if not token:
            return None, None
            
        user_id = self.user_manager.authenticate(token)
        if not user_id:
            return None, None
        
        # Lazy load PantryManager for this user
        if user_id not in self.pantry_managers:
            db_path = self.user_manager.get_user_db_path(user_id)
            self.pantry_managers[user_id] = PantryManager(db_path)
            
            # Initialize database if it doesn't exist
            from db_setup import setup_database
            setup_database(db_path)
        
        return user_id, self.pantry_managers[user_id]
    
    def set_current_user(self, user_id: str):
        """Set the current user in context."""
        current_user.set(user_id)
    
    def get_current_user(self) -> Optional[str]:
        """Get the current user from context."""
        return current_user.get()
    
    def create_user(self, username: str, admin_token: str) -> Dict[str, Any]:
        """Create a new user (admin only)."""
        # Verify admin token
        admin_user = self.user_manager.authenticate(admin_token)
        if admin_user != "admin":
            return {"status": "error", "message": "Admin access required"}
        
        try:
            token = self.user_manager.create_user(username)
            return {"status": "success", "token": token, "username": username}
        except ValueError as e:
            return {"status": "error", "message": str(e)}