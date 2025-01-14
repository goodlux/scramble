// Memory and Entity Schema for scRAMble

// Node Constraints
CREATE CONSTRAINT entry_id IF NOT EXISTS FOR (e:Entry) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE;

// Node Indexes
CREATE INDEX entry_timestamp IF NOT EXISTS FOR (e:Entry) ON (e.created_at);
CREATE INDEX entry_type IF NOT EXISTS FOR (e:Entry) ON (e.type);
CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type);

// Schema Comments
/*
Node Properties:

Entry {
    id: string,              // UUID
    type: string,            // conversation, document, etc
    content: string,         // The actual content
    created_at: datetime,    // Creation timestamp
    metadata: map,           // Flexible metadata storage
    vector_id: string        // ChromaDB reference
}

Entity {
    name: string,            // Unique entity name
    type: string,            // Entity type (person, place, concept, etc)
    source: string,          // Where entity was first identified
    confidence: float,       // Entity detection confidence
    metadata: map           // Additional entity information
}

Relationships:
:MENTIONS          // Entry mentions an Entity
:CONTINUES        // Entry is continuation of another Entry (e.g. conversation thread)
:RELATED_TO       // Entity is related to another Entity
:DERIVED_FROM     // Entry was derived from another Entry
*/

// Cleanup Note:
// In a migration scenario, you might want to:
// 1. MATCH any existing (:Conversation) nodes and add :Entry label
// 2. Convert relevant :NEXT_IN_SEQUENCE relationships to :CONTINUES
// 3. Extract topics as entities with :DISCUSSES becoming :MENTIONS