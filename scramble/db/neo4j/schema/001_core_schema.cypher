// Core Schema - Shared Knowledge Structure

// Node Constraints
CREATE CONSTRAINT conversation_id IF NOT EXISTS FOR (c:Conversation) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT topic_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE;
CREATE CONSTRAINT model_id IF NOT EXISTS FOR (m:Model) REQUIRE m.model_id IS UNIQUE;
CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE;

// TODO(living-room): Add constraints for:
// CREATE CONSTRAINT room_id IF NOT EXISTS FOR (r:Room) REQUIRE r.id IS UNIQUE;
// CREATE CONSTRAINT cat_toy_id IF NOT EXISTS FOR (t:CatToy) REQUIRE t.id IS UNIQUE;

// Node Indexes
CREATE INDEX conversation_timestamp IF NOT EXISTS FOR (c:Conversation) ON (c.timestamp);
CREATE INDEX topic_search IF NOT EXISTS FOR (t:Topic) ON (t.name, t.description);
CREATE INDEX model_search IF NOT EXISTS FOR (m:Model) ON (m.model_name);

// TODO(living-room): Add indexes for room-specific queries
// CREATE INDEX room_activity IF NOT EXISTS FOR (r:Room) ON (r.last_active);

// Schema Comments
/*
Core Node Properties:

Conversation {
  id: string,              // UUID
  content: string,         // The actual message
  timestamp: datetime,     // When created
  metadata: map,           // Flexible metadata
  vector_id: string,       // ChromaDB reference
  type: string,           // Message type
  context: string         // TODO(living-room): Add room context
}

// TODO(living-room): Room Schema
Room {
  id: string,           // Room identifier
  name: string,         // Room name
  type: string,         // Room type (general, quiet, playground)
  created_at: datetime, // Creation timestamp
  last_active: datetime // Last activity
}

Relationships:
:NEXT_IN_SEQUENCE    // Message threading
:DISCUSSES           // Topic linking
:GENERATED_BY        // Model attribution
:REFERENCES          // Cross-references
:RELATED_TO          // Topic relationships
:HAS_ACCESS          // Access control

TODO(living-room): Additional Relationships:
:IN_ROOM            // Message/User to Room
:PLAYS_WITH         // User to CatToy
:MODERATES          // Nomena to Room
*/