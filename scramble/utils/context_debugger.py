"""Debugging tools for context visibility in models."""
from typing import Dict, Any, Optional, List
import json
from datetime import datetime, UTC
import os
import pathlib
from scramble.utils.logging import get_logger

logger = get_logger(__name__)

class ContextDebugger:
    """Utility for debugging context sent to models."""
    
    def __init__(self):
        """Initialize with default settings."""
        self.debug_mode = False
        self.last_context = None
        self.context_log = []
        self.max_log_entries = 10
        
        # Set up logging directory
        # First try user's repo path, fallback to home directory
        repo_path = os.path.expanduser("~/repos/scramble")
        if os.path.exists(repo_path):
            self.log_dir = os.path.join(repo_path, "logs/context_dumps")
        else:
            self.log_dir = os.path.expanduser("~/.scramble/logs/context_dumps")
        
        # Create the directory at initialization
        self.ensure_log_directory()
        logger.info(f"Context debugger initialized with log directory: {self.log_dir}")
    
    def toggle_debug_mode(self) -> bool:
        """Toggle debug mode on/off."""
        self.debug_mode = not self.debug_mode
        logger.info(f"Context debug mode: {'ENABLED' if self.debug_mode else 'DISABLED'}")
        return self.debug_mode
    
    def ensure_log_directory(self) -> None:
        """Make sure the logging directory exists."""
        try:
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir, exist_ok=True)
                logger.info(f"Created context logging directory: {self.log_dir}")
        except Exception as e:
            logger.error(f"Failed to create context logging directory: {e}")
    
    def record_context(self, context: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record a context instance for debugging to file system."""
        # Make sure the logging directory exists
        self.ensure_log_directory()
        
        self.last_context = context
        timestamp = datetime.now(UTC)
        formatted_time = timestamp.strftime("%Y%m%d_%H%M%S")
        
        # Create an entry with metadata
        entry = {
            "timestamp": timestamp.isoformat(),
            "context_length": len(context),
            "context": context,
            "metadata": metadata or {}
        }
        
        # Add to in-memory log, maintaining max size
        self.context_log.append(entry)
        if len(self.context_log) > self.max_log_entries:
            self.context_log.pop(0)  # Remove oldest entry
        
        # Save to file in the logs directory
        model_name = metadata.get("model", "unknown_model") if metadata else "unknown_model"
        filename = f"context_{formatted_time}_{model_name}.txt"
        file_path = os.path.join(self.log_dir, filename)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                # Write a header
                f.write(f"============ CONTEXT DUMP [{formatted_time}] ============\n")
                f.write(f"Model: {model_name}\n")
                f.write(f"Context Length: {len(context)} characters\n")
                
                # Include metadata if available
                if metadata:
                    f.write("\nMetadata:\n")
                    for key, value in metadata.items():
                        f.write(f"  {key}: {value}\n")
                
                # Write the full context
                f.write("\n=========== CONTEXT CONTENT ===========\n")
                f.write(context)
                f.write("\n=======================================\n")
            
            # Create a JSON version with the same metadata
            json_path = os.path.join(self.log_dir, f"context_{formatted_time}_{model_name}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(entry, f, indent=2)
            
            logger.info(f"Saved context dump to {file_path} and {json_path}")
            return
        except Exception as e:
            logger.error(f"Error saving context dump to file: {e}")
            
        logger.info(f"Recorded context: {len(context)} characters")
    
    def get_last_context(self) -> Optional[str]:
        """Get the most recently recorded context."""
        return self.last_context
    
    def get_context_summary(self) -> str:
        """Get a summary of recent context records."""
        if not self.context_log:
            return "No context records available."
        
        summary_lines = ["Recent context records:"]
        for i, entry in enumerate(reversed(self.context_log), 1):
            timestamp = entry["timestamp"].split('T')[1].split('.')[0]  # Extract time only
            summary_lines.append(
                f"{i}. [{timestamp}] Length: {entry['context_length']} chars, "
                f"Model: {entry['metadata'].get('model', 'unknown')}"
            )
        
        return "\n".join(summary_lines)
    
    def format_context_dump(self, include_full: bool = False) -> str:
        """Format the most recent context for readable output."""
        if not self.last_context:
            return "No context available. Send a message first."
        
        lines = ["=== CONTEXT DUMP ==="]
        lines.append(f"Total length: {len(self.last_context)} characters")
        
        # Show the first 500 characters by default
        if include_full:
            lines.append("\nFULL CONTEXT:")
            lines.append(self.last_context)
        else:
            lines.append("\nCONTEXT PREVIEW (first 500 chars):")
            lines.append(self.last_context[:500] + "...")
            lines.append("\nUse '/debug full' to see complete context")
        
        lines.append("=== END CONTEXT DUMP ===")
        return "\n".join(lines)

# Create a singleton instance
context_debugger = ContextDebugger()
