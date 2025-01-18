"""Configuration management for the Scramble system."""
from typing import Optional, Dict, Any
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

class Config:
    # Debug settings
    DEBUG_SESSION: bool = bool(os.getenv("DEBUG_SESSION", ""))  # Empty string evaluates to False

    # Deployment Mode
    DEPLOYMENT_MODE: str = os.getenv("DEPLOYMENT_MODE", "scramble")  # or "living-room"
    
    # Digital Trinity Settings - Shared Infrastructure
    NEO4J_HOST: str = os.getenv("NEO4J_HOST", "localhost")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    
    # Neo4j settings
    NEO4J_URI: str = f"bolt://{NEO4J_HOST}:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "scR4Mble#Graph!")
    
    # Redis settings
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Mock LLM settings
    DISABLE_MOCK_LLM: bool = bool(os.getenv("DISABLE_MOCK_LLM", "true"))
    
    @classmethod
    def is_living_room(cls) -> bool:
        """Check if we're in living room mode"""
        return cls.DEPLOYMENT_MODE == "living-room"
    
    @classmethod
    def get_neo4j_config(cls) -> Dict[str, str]:
        """Get Neo4j connection configuration"""
        config = {
            "uri": cls.NEO4J_URI,
            "user": cls.NEO4J_USER,
            "password": cls.NEO4J_PASSWORD
        }
        return config

    @classmethod
    def get_redis_config(cls) -> Dict[str, Any]:
        """Get Redis configuration"""
        config = {
            "host": cls.REDIS_HOST,
            "port": cls.REDIS_PORT,
            "db": cls.REDIS_DB
        }
        return config

# Global config instance
config = Config()