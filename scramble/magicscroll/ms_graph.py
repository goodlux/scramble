"""Neo4j graph operations for MagicScroll."""
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import asyncio
from neo4j import AsyncGraphDatabase, AsyncDriver, Query
from neo4j.exceptions import Neo4jError
from scramble.utils.logging import get_logger
from .ms_entry import MSEntry
from typing_extensions import LiteralString
from typing import cast

logger = get_logger(__name__)

def literal_query(text: str) -> Query:
    """Create a Query object from a string, casting to LiteralString."""
    return Query(cast(LiteralString, text))

class MSGraphManager:
    """Handles Neo4j graph operations for MagicScroll."""
    
    def __init__(self, neo4j_driver: AsyncDriver):
        """Initialize with Neo4j driver."""
        self.driver = neo4j_driver

    async def init_schema(self) -> None:
        """Initialize Neo4j schema with indexes."""
        try:
            async with self.driver.session() as session:
                # Create constraints
                await session.run(
                    literal_query("""
                    CREATE CONSTRAINT entry_id IF NOT EXISTS
                    FOR (e:Entry) REQUIRE e.id IS UNIQUE
                    """)
                )
                
                await session.run(
                    literal_query("""
                    CREATE CONSTRAINT entity_name IF NOT EXISTS
                    FOR (e:Entity) REQUIRE e.name IS UNIQUE
                    """)
                )
                
                # Create indexes
                await session.run(
                    literal_query("""
                    CREATE INDEX entry_timestamp IF NOT EXISTS
                    FOR (e:Entry) ON (e.created_at)
                    """)
                )
                
                await session.run(
                    literal_query("""
                    CREATE INDEX entry_type IF NOT EXISTS
                    FOR (e:Entry) ON (e.type)
                    """)
                )
                
        except Neo4jError as e:
            logger.error(f"Error initializing Neo4j schema: {e}")
            raise
        
    async def create_entry_node(
        self,
        entry: MSEntry,
        content: str,
        parent_id: Optional[str] = None,
        entities: Optional[List[str]] = None,
        entry_id: Optional[str] = None  # Added this parameter
    ) -> bool:
        """Create a new entry node with relationships."""
        try:
            async with self.driver.session() as session:
                # Create entry node
                await session.run(
                    literal_query("""
                    CREATE (e:Entry {
                        id: $id,
                        type: $type,
                        content: $content,
                        created_at: datetime($timestamp)
                    })
                    """),
                    id=entry_id or entry.id,  # Use provided ID if available
                    type=entry.entry_type.value,
                    content=content,
                    timestamp=entry.created_at.isoformat()
                )
                
                # Create parent relationship if exists
                if parent_id:
                    await session.run(
                        literal_query("""
                        MATCH (child:Entry {id: $child_id})
                        MATCH (parent:Entry {id: $parent_id})
                        CREATE (child)-[:CONTINUES]->(parent)
                        """),
                        child_id=entry_id or entry.id,  # Use consistent ID
                        parent_id=parent_id
                    )
                
                # Create entity relationships
                if entities:
                    await session.run(
                        literal_query("""
                        MATCH (e:Entry {id: $entry_id})
                        UNWIND $entities as entity_name
                        MERGE (ent:Entity {name: entity_name})
                        CREATE (e)-[:MENTIONS]->(ent)
                        """),
                        entry_id=entry_id or entry.id,  # Use consistent ID
                        entities=entities
                    )
                
                return True
                
        except Neo4jError as e:
            logger.error(f"Error creating entry node: {e}")
            return False

    async def get_conversation_thread(
        self,
        entry_id: str,
        max_depth: int = 5
    ) -> List[MSEntry]:
        """Get the conversation thread for an entry."""
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    literal_query("""
                    MATCH path = (start:Entry {id: $entry_id})
                        -[:CONTINUES*..{max_depth}]-(related:Entry)
                    WITH nodes(path) as entries
                    UNWIND entries as entry
                    RETURN DISTINCT entry
                    ORDER BY entry.created_at
                    """),
                    entry_id=entry_id,
                    max_depth=max_depth
                )
                
                entries = []
                async for record in result:
                    entry_data = record["entry"]
                    entries.append(MSEntry.from_neo4j(entry_data))
                
                return entries
                
        except Neo4jError as e:
            logger.error(f"Error getting conversation thread: {e}")
            return []

    async def find_related_entries(
        self,
        entry_id: str,
        max_entity_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """Find entries related through shared entities."""
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    literal_query("""
                    MATCH (e:Entry {id: $entry_id})
                    
                    // Find entries sharing entities
                    OPTIONAL MATCH (e)-[:MENTIONS]->(ent:Entity)
                        <-[:MENTIONS]-(related:Entry)
                    WHERE related.id <> e.id
                    
                    // Include entity path information
                    RETURN related,
                           collect(DISTINCT ent.name) as shared_entities,
                           count(DISTINCT ent) as entity_overlap
                    ORDER BY entity_overlap DESC
                    LIMIT 10
                    """),
                    entry_id=entry_id
                )
                
                related = []
                async for record in result:
                    if record["related"]:
                        related.append({
                            'entry': MSEntry.from_neo4j(record["related"]),
                            'shared_entities': record["shared_entities"],
                            'overlap_score': record["entity_overlap"]
                        })
                
                return related
                
        except Neo4jError as e:
            logger.error(f"Error finding related entries: {e}")
            return []