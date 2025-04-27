from typing import List, Dict, Any, Optional
import sqlite3
import json
from datetime import datetime, UTC
import uuid
from pathlib import Path

from .ms_entry import MSConversation

class MSFIPAStorage:
    """FIPA message storage handled by MagicScroll."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize FIPA storage with optional custom path."""
        self.db_path = db_path or str(Path.home() / ".scramble" / "fipa_messages.db")
        self._initialize_db()
        
    def _initialize_db(self):
        """Set up the SQLite database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create conversations table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS fipa_conversations (
            conversation_id TEXT PRIMARY KEY,
            start_time TEXT,
            end_time TEXT,
            metadata TEXT
        )
        ''')
        
        # Create messages table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS fipa_messages (
            message_id TEXT PRIMARY KEY,
            conversation_id TEXT,
            sender TEXT,
            receiver TEXT,
            content TEXT,
            performative TEXT,
            timestamp TEXT,
            metadata TEXT,
            FOREIGN KEY (conversation_id) REFERENCES fipa_conversations (conversation_id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_conversation(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new FIPA conversation and return its ID."""
        conversation_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO fipa_conversations VALUES (?, ?, ?, ?)",
            (
                conversation_id,
                datetime.now(UTC).isoformat(),
                None,
                json.dumps(metadata or {})
            )
        )
        
        conn.commit()
        conn.close()
        return conversation_id
    
    def save_message(self, 
                    conversation_id: str,
                    sender: str,
                    receiver: str,
                    content: str,
                    performative: str = "INFORM",
                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """Save a FIPA message to the database."""
        message_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        metadata = metadata or {}
        
        cursor.execute(
            "INSERT INTO fipa_messages VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                message_id,
                conversation_id,
                sender,
                receiver,
                content,
                performative,
                datetime.now(UTC).isoformat(),
                json.dumps(metadata)
            )
        )
        
        conn.commit()
        conn.close()
        return message_id
    
    def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a conversation."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM fipa_messages WHERE conversation_id = ? ORDER BY timestamp",
            (conversation_id,)
        )
        
        messages = []
        for row in cursor.fetchall():
            message = dict(row)
            message["metadata"] = json.loads(message["metadata"])
            messages.append(message)
        
        conn.close()
        return messages
    
    def close_conversation(self, conversation_id: str) -> bool:
        """Mark a conversation as closed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE fipa_conversations SET end_time = ? WHERE conversation_id = ?",
            (datetime.now(UTC).isoformat(), conversation_id)
        )
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def get_filtered_conversation(self, conversation_id: str, 
                                include_ephemeral: bool = False) -> List[Dict[str, Any]]:
        """Get messages from a conversation, optionally filtering out ephemeral ones."""
        messages = self.get_conversation_messages(conversation_id)
        
        if not include_ephemeral:
            messages = [
                msg for msg in messages 
                if not msg["metadata"].get("message_type") == "EPHEMERAL"
            ]
            
        return messages
