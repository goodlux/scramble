# Neo4j Schema for scRAMble

This directory contains the Neo4j schema definitions for scRAMble's graph database.

## Files

### 001_core_schema.cypher
Base schema for conversations, topics, and models:
- Node constraints and indexes
- Core relationship types
- Conversation flow structure

### 002_document_schema.cypher
Schema for document storage and relationships:
- Document, Image, and Code nodes
- Content relationship types
- Redis integration properties

### 003_memory_schema.cypher
Enhanced memory and entity tracking:
- Entry and Entity nodes
- Memory relationships
- Enhanced temporal tracking

## Running the Schema

To apply the schema to a new Neo4j database:

1. Start Neo4j
2. Run the schema files in order:

```bash
cat schema/001_core_schema.cypher | cypher-shell -u neo4j -p your_password
cat schema/002_document_schema.cypher | cypher-shell -u neo4j -p your_password
cat schema/003_memory_schema.cypher | cypher-shell -u neo4j -p your_password
```

Or using the Neo4j Browser, copy and paste the contents of each file in order.

## Schema Visualization

You can visualize the schema in Neo4j Browser using:

```cypher
CALL db.schema.visualization()
```

## Relationship Types

The schema defines several relationship types for different purposes:

### Core Relationships
- :NEXT_IN_SEQUENCE - Temporal conversation flow
- :DISCUSSES - Content to Topic connections
- :GENERATED_BY - Model attribution
- :REFERENCES - Cross-references
- :HAS_ACCESS - Access control

### Document Relationships
- :EXTRACTED_FROM - Content extraction tracking
- :REFERENCED_IN - Content references
- :DERIVED_FROM - Content derivation
- :CONTAINS - Content composition
- :IMPLEMENTS - Code implementation links
- :ILLUSTRATES - Image illustration links

### Memory Relationships
- :MENTIONS - Entry to Entity connections
- :CONTINUES - Sequential relationship between Entries
- :RELATED_TO - Entity to Entity connections