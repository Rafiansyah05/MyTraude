"""
Session manager for in-memory user session storage.
Handles temporary session data with auto-cleanup.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass, field

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SessionData:
    """User trading session data (stored in RAM)."""
    user_id: int
    capital: int
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    screening_results: list = field(default_factory=list)
    selected_stocks: list = field(default_factory=list)
    analysis_results: dict = field(default_factory=dict)
    
    def is_expired(self, timeout_minutes: int) -> bool:
        """Check if session is expired."""
        elapsed = (datetime.now() - self.last_activity).total_seconds() / 60
        return elapsed > timeout_minutes
    
    def touch(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()


class SessionManager:
    """Manage in-memory user sessions."""
    
    _sessions: Dict[int, SessionData] = {}
    _cleanup_task: Optional[asyncio.Task] = None
    
    @classmethod
    def create_session(cls, user_id: int, capital: int) -> SessionData:
        """
        Create new session for user.
        
        Args:
            user_id: Telegram user ID
            capital: Trading capital amount
        
        Returns:
            SessionData object
        """
        session = SessionData(user_id=user_id, capital=capital)
        cls._sessions[user_id] = session
        logger.info(f"Session created for user {user_id}, capital: {capital}")
        return session
    
    @classmethod
    def get_session(cls, user_id: int) -> Optional[SessionData]:
        """Get user's current session."""
        session = cls._sessions.get(user_id)
        if session and session.is_expired(settings.SESSION_TIMEOUT_MINUTES):
            logger.info(f"Session expired for user {user_id}")
            cls._sessions.pop(user_id, None)
            return None
        
        if session:
            session.touch()
        
        return session
    
    @classmethod
    def update_session(cls, user_id: int, **kwargs) -> bool:
        """
        Update session data.
        
        Args:
            user_id: User ID
            **kwargs: Fields to update
        
        Returns:
            True if updated, False if session not found
        """
        session = cls.get_session(user_id)
        if not session:
            return False
        
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)
        
        session.touch()
        return True
    
    @classmethod
    def end_session(cls, user_id: int) -> bool:
        """
        End user's session and clean up.
        
        Args:
            user_id: User ID
        
        Returns:
            True if session was ended
        """
        if user_id in cls._sessions:
            cls._sessions.pop(user_id)
            logger.info(f"Session ended for user {user_id}")
            return True
        return False
    
    @classmethod
    async def cleanup_expired_sessions(cls):
        """
        Periodically clean up expired sessions.
        Should be run as background task.
        """
        while True:
            try:
                await asyncio.sleep(settings.SESSION_CLEANUP_INTERVAL)
                
                expired_users = [
                    user_id for user_id, session in cls._sessions.items()
                    if session.is_expired(settings.SESSION_TIMEOUT_MINUTES)
                ]
                
                for user_id in expired_users:
                    cls._sessions.pop(user_id, None)
                    logger.debug(f"Cleaned up expired session for user {user_id}")
                
                if expired_users:
                    logger.info(f"Cleaned {len(expired_users)} expired sessions")
            
            except Exception as e:
                logger.error(f"Error in cleanup_expired_sessions: {e}")
    
    @classmethod
    def start_cleanup_task(cls):
        """Start background cleanup task."""
        if cls._cleanup_task is None or cls._cleanup_task.done():
            cls._cleanup_task = asyncio.create_task(cls.cleanup_expired_sessions())
            logger.info("Session cleanup task started")
    
    @classmethod
    async def stop_cleanup_task(cls):
        """Stop background cleanup task."""
        if cls._cleanup_task and not cls._cleanup_task.done():
            cls._cleanup_task.cancel()
            try:
                await cls._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Session cleanup task stopped")
    
    @classmethod
    def get_active_sessions(cls) -> int:
        """Get count of active sessions."""
        return len(cls._sessions)
    
    @classmethod
    def clear_all_sessions(cls):
        """Clear all sessions (for testing/shutdown)."""
        cls._sessions.clear()
        logger.info("All sessions cleared")
