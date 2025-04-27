import os
import sqlite3
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path

from llama_index.core import Document, Settings

from .ms_entry import MSEntry, EntryType
from scramble.config import Config
from scramble.utils.logging import get_logger

logger = get_logger(__name__)

# Default SQLite database path
DEFAULT_DB_PATH = os.path.expanduser("~/.scramble/magicscroll.db")

# Import sqlite_vec module
import sqlite_vec

class SQLiteVecLoader:
    """Helper class to load the sqlite-vec extension."""
    
    @staticmethod
    def load_extension(conn: sqlite3.Connection) -> bool:
        """Load the sqlite-vec extension using the pip package."""
        try:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            logger.info("Loaded sqlite-vec extension")
            return True
        except Exception as e:
            logger.error(f"Error loading sqlite-vec extension: {e}")
            return False
        finally:
            try:
                conn.enable_load_extension(False)
            except Exception:
                pass


class MSSQLiteStore:
    """SQLite storage for MagicScroll with vector search support."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize SQLite storage."""
        self.db_path = db_path or DEFAULT_DB_PATH
        self._ensure_directory_exists()
        
        self.conn = self._create_connection()
        self.has_vec_extension = SQLiteVecLoader.load_extension(self.conn)
        
        # Initialize tables
        self._init_tables()
        
        # Set up embedding model reference
        self.embed_model = Settings.embed_model
        
        logger.info(f"SQLite store initialized at {self.db_path}")
        if self.has_vec_extension:
            logger.info("Vector search capabilities enabled")
        else:
            logger.warning("Vector search NOT available - install with: pip install sqlite-vec")
    
    def _ensure_directory_exists(self):
        """Make sure the directory for the database exists."""
        db_dir = os.path.dirname(self.db_path)
        os.makedirs(db_dir, exist_ok=True)
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a connection to the SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Make rows accessible by column name
            return conn
        except sqlite3.Error as e:
            logger.error(f"Error connecting to SQLite database: {e}")
            raise
    
    def _init_tables(self):
        """Initialize database tables."""
        try:
            cursor = self.conn.cursor()
            
            # Create entries table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS entries (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                metadata TEXT NOT NULL
            )
            ''')
            
            # Create vector table if extension is available
            if self.has_vec_extension:
                try:
                    # Try to create the vss0 virtual table
                    cursor.execute('''
                    CREATE VIRTUAL TABLE IF NOT EXISTS entry_vectors USING vss0(
                        id TEXT,
                        embedding BLOB,
                        dimensions INTEGER,
                        distance_function TEXT,
                        PRIMARY KEY(id),
                        FOREIGN KEY(id) REFERENCES entries(id) ON DELETE CASCADE
                    )
                    ''')
                    logger.info("Created entry_vectors table using vss0")
                except sqlite3.OperationalError as e:
                    logger.warning(f"Error creating vss0 table: {e}")
                    try:
                        # Try older vec0 format as fallback
                        cursor.execute('''
                        CREATE VIRTUAL TABLE IF NOT EXISTS entry_vectors USING vec0(
                            id TEXT,
                            embedding BLOB,
                            PRIMARY KEY(id),
                            FOREIGN KEY(id) REFERENCES entries(id) ON DELETE CASCADE
                        )
                        ''')
                        logger.info("Created entry_vectors table using vec0")
                    except sqlite3.OperationalError as e2:
                        logger.error(f"Error creating vec0 table: {e2}")
                        self.has_vec_extension = False
                        logger.warning("Vector search will be unavailable")
            
            # If vector extension somehow isn't available, log error
            if not self.has_vec_extension:
                logger.error("Vector extension could not be loaded - search will not work properly!")
                logger.error("Please reinstall sqlite-vec with: pip install --force-reinstall sqlite-vec")
            
            self.conn.commit()
            logger.info("Database tables initialized")
        except sqlite3.Error as e:
            logger.error(f"Error initializing database tables: {e}")
            self.conn.rollback()
            raise
    
    @classmethod
    async def create(cls, db_path: Optional[str] = None) -> 'MSSQLiteStore':
        """Factory method to create store instance."""
        return cls(db_path)
    
    async def save_ms_entry(self, entry: MSEntry) -> bool:
        """Store a MagicScroll entry with vector embedding."""
        try:
            cursor = self.conn.cursor()
            
            # Convert metadata to JSON string
            metadata_json = json.dumps(entry.metadata)
            created_at_iso = entry.created_at.isoformat()
            
            # Insert/update entry in the main table
            cursor.execute('''
            INSERT OR REPLACE INTO entries (id, content, entry_type, created_at, metadata)
            VALUES (?, ?, ?, ?, ?)
            ''', (entry.id, entry.content, entry.entry_type.value, created_at_iso, metadata_json))
            
            # If vector extension is available, store embedding
            if self.has_vec_extension and self.embed_model:
                try:
                    # Generate embedding
                    embedding = await self.embed_model.aget_text_embedding(entry.content)
                    
                    # First try with sqlite_vec's serialize_float32
                    try:
                        import sqlite_vec
                        embedding_blob = sqlite_vec.serialize_float32(embedding)
                    except (ImportError, AttributeError):
                        # Fallback to numpy if sqlite_vec isn't available
                        import numpy as np
                        embedding_blob = np.array(embedding, dtype=np.float32).tobytes()
                    
                    try:
                        # Try vss0 format
                        cursor.execute('''
                        INSERT OR REPLACE INTO entry_vectors (id, embedding, dimensions, distance_function)
                        VALUES (?, ?, ?, ?)
                        ''', (entry.id, embedding_blob, len(embedding), 'cosine'))
                    except sqlite3.OperationalError:
                        # Try vec0 format
                        cursor.execute('''
                        INSERT OR REPLACE INTO entry_vectors (id, embedding)
                        VALUES (?, ?)
                        ''', (entry.id, embedding_blob))
                    
                    logger.info(f"Entry {entry.id} stored with vector embedding")
                except Exception as vec_err:
                    logger.error(f"Error storing entry with vector: {vec_err}")
            
            self.conn.commit()
            logger.info(f"Entry {entry.id} stored successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error storing entry: {e}")
            self.conn.rollback()
            return False
    
    async def get_ms_entry(self, entry_id: str) -> Optional[MSEntry]:
        """Retrieve a MagicScroll entry."""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute('''
            SELECT id, content, entry_type, created_at, metadata
            FROM entries
            WHERE id = ?
            ''', (entry_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            # Parse the row data
            metadata = json.loads(row['metadata'])
            
            # Convert to Document
            doc = Document(
                text=row['content'],
                doc_id=row['id'],
                metadata={
                    "type": row['entry_type'],
                    "created_at": row['created_at'],
                    **metadata
                }
            )
            
            # Convert document to MSEntry
            return MSEntry.from_document(doc)
            
        except Exception as e:
            logger.error(f"Error retrieving entry: {e}")
            return None
    
    async def delete_ms_entry(self, entry_id: str) -> bool:
        """Delete a MagicScroll entry."""
        try:
            cursor = self.conn.cursor()
            
            # Delete from main table (will cascade delete from vector table)
            cursor.execute('DELETE FROM entries WHERE id = ?', (entry_id,))
            
            self.conn.commit()
            logger.info(f"Entry {entry_id} deleted")
            return True
        except Exception as e:
            logger.error(f"Error deleting entry: {e}")
            self.conn.rollback()
            return False
    
    async def search_by_vector(self, query_embedding, limit: int = 5) -> List[Dict[str, Any]]:
        """Search entries by vector similarity."""
        if not self.has_vec_extension:
            logger.error("Vector search not available - search will not work!")
            logger.error("Please reinstall sqlite-vec with: pip install --force-reinstall sqlite-vec")
            return []
            
        try:
            cursor = self.conn.cursor()
            
            # First try with sqlite_vec's serialize_float32
            try:
                import sqlite_vec
                query_blob = sqlite_vec.serialize_float32(query_embedding)
            except (ImportError, AttributeError):
                # Fallback to numpy if sqlite_vec isn't available
                import numpy as np
                query_blob = np.array(query_embedding, dtype=np.float32).tobytes()
            
            # Try different search functions based on what's available
            try:
                # First try vss_cosine_similarity
                cursor.execute('''
                SELECT e.id, e.content, e.entry_type, e.created_at, e.metadata,
                       vss_cosine_similarity(v.embedding, ?) as score
                FROM entries e
                JOIN entry_vectors v ON e.id = v.id
                ORDER BY score DESC
                LIMIT ?
                ''', (query_blob, limit))
            except sqlite3.OperationalError:
                try:
                    # Try vec_dot_product
                    cursor.execute('''
                    SELECT e.id, e.content, e.entry_type, e.created_at, e.metadata,
                           vec_dot_product(v.embedding, ?) as score
                    FROM entries e
                    JOIN entry_vectors v ON e.id = v.id
                    ORDER BY score DESC
                    LIMIT ?
                    ''', (query_blob, limit))
                except sqlite3.OperationalError:
                    # Fall back to match operator if available (EXPERIMENTAL)
                    try:
                        cursor.execute('''
                        SELECT e.id, e.content, e.entry_type, e.created_at, e.metadata,
                               distance as score
                        FROM entries e
                        JOIN entry_vectors v ON e.id = v.id
                        WHERE v.embedding MATCH ?
                        ORDER BY score
                        LIMIT ?
                        ''', (query_blob, limit))
                    except sqlite3.OperationalError:
                        # Last resort: just return most recent entries
                        logger.warning("No vector search function available - returning recent entries instead")
                        cursor.execute('''
                        SELECT id, content, entry_type, created_at, metadata, 0.5 as score
                        FROM entries
                        ORDER BY created_at DESC
                        LIMIT ?
                        ''', (limit,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row['id'],
                    "score": float(row['score']),
                    "content": row['content'],
                    "entry_type": row['entry_type'],
                    "created_at": datetime.fromisoformat(row['created_at']),
                    "metadata": json.loads(row['metadata'])
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []
    
    async def get_recent_entries(
        self, 
        hours: Optional[int] = None,
        entry_types: Optional[List[EntryType]] = None,
        limit: int = 10
    ) -> List[MSEntry]:
        """Get recent entries from the store."""
        try:
            cursor = self.conn.cursor()
            
            # Build the query
            query = '''
            SELECT id, content, entry_type, created_at, metadata
            FROM entries
            '''
            
            # Add conditions
            conditions = []
            params = []
            
            # Time filter
            if hours is not None:
                cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
                conditions.append("created_at >= ?")
                params.append(cutoff_time)
            
            # Entry type filter
            if entry_types:
                type_placeholders = ", ".join(["?" for _ in entry_types])
                conditions.append(f"entry_type IN ({type_placeholders})")
                params.extend([t.value for t in entry_types])
            
            # Add WHERE clause if we have conditions
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            # Add order and limit
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            # Execute query
            cursor.execute(query, params)
            
            # Process results
            entries = []
            for row in cursor.fetchall():
                # Convert to Document and then to MSEntry
                metadata = json.loads(row['metadata'])
                doc = Document(
                    text=row['content'],
                    doc_id=row['id'],
                    metadata={
                        "type": row['entry_type'],
                        "created_at": row['created_at'],
                        **metadata
                    }
                )
                entries.append(MSEntry.from_document(doc))
            
            return entries
            
        except Exception as e:
            logger.error(f"Error getting recent entries: {e}")
            return []
    
    async def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("SQLite connection closed")

    def __del__(self):
        """Make sure connection is closed on deletion."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
