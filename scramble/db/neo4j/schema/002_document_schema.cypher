// Document Schema for scRAMble - Document, Image, and Code Structure

// Node Constraints
CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT image_id IF NOT EXISTS FOR (i:Image) REQUIRE i.id IS UNIQUE;
CREATE CONSTRAINT code_id IF NOT EXISTS FOR (c:Code) REQUIRE c.id IS UNIQUE;

// Node Indexes
CREATE INDEX document_search IF NOT EXISTS FOR (d:Document) ON (d.title, d.format);
CREATE INDEX code_search IF NOT EXISTS FOR (c:Code) ON (c.language, c.filename);
CREATE INDEX content_hash_search IF NOT EXISTS FOR (d:Document) ON (d.content_hash);

// Schema Comments
/*
Node Properties:

Document {
  id: string,              // UUID
  content_hash: string,    // Redis key/hash
  title: string,           // Document title
  format: string,          // File format/type
  created_at: datetime,    // Creation timestamp
  updated_at: datetime,    // Last update
  metadata: map,           // Flexible metadata
  vector_id: string,       // ChromaDB vector reference
  location: string         // Redis storage location
}

Image {
  id: string,              // UUID
  content_hash: string,    // Redis key/hash
  format: string,          // Image format (png, jpg, etc)
  dimensions: string,      // Image dimensions
  created_at: datetime,    // Creation timestamp
  metadata: map,           // EXIF and other metadata
  vector_id: string,       // ChromaDB vector reference
  location: string         // Redis storage location
}

Code {
  id: string,              // UUID
  content_hash: string,    // Redis key/hash
  language: string,        // Programming language
  filename: string,        // Original filename
  created_at: datetime,    // Creation timestamp
  updated_at: datetime,    // Last modification
  metadata: map,           // Code-specific metadata
  vector_id: string,       // ChromaDB vector reference
  location: string         // Redis storage location
}

Relationships:
:EXTRACTED_FROM     // Document/Code/Image was extracted from a Conversation
:REFERENCED_IN      // Document/Code/Image is referenced in a Conversation
:DERIVED_FROM       // Document was derived from another Document
:CONTAINS           // Document contains Image or Code
:IMPLEMENTS         // Code implements something described in a Document
:ILLUSTRATES        // Image illustrates content in a Document
*/