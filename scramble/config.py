from typing import Optional, Dict, Any
import os

class Config:
    # Deployment Mode
    DEPLOYMENT_MODE: str = os.getenv("DEPLOYMENT_MODE", "scramble")  # or "living-room"
    
    # Digital Trinity Settings - Shared Infrastructure
    NEO4J_HOST: str = os.getenv("NEO4J_HOST", "localhost")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    CHROMA_HOST: str = os.getenv("CHROMA_HOST", "localhost")
    
    # Neo4j settings
    NEO4J_URI: str = f"bolt://{NEO4J_HOST}:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "scR4Mble#Graph!")
    
    # Redis settings
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # ChromaDB settings
    CHROMA_PORT: int = 8000
    
    # TODO(living-room): Nomena's Configuration
    # CAT_MOOD: str = os.getenv("CAT_MOOD", "SLEEPING")
    # ROOM_TYPE: str = os.getenv("ROOM_TYPE", "cozy")
    # AUTH_MODE: str = os.getenv("AUTH_MODE", "none")
    
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
        # TODO(living-room): Add room-specific database if needed
        # if cls.is_living_room():
        #     config["database"] = "living_room"
        return config

    @classmethod
    def get_redis_config(cls) -> Dict[str, Any]:
        """Get Redis configuration"""
        config = {
            "host": cls.REDIS_HOST,
            "port": cls.REDIS_PORT,
            "db": cls.REDIS_DB
        }
        # TODO(living-room): Add room-specific Redis DB if needed
        # if cls.is_living_room():
        #     config["db"] = 1
        return config

# Global config instance
config = Config()