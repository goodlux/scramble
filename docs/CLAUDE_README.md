# LlamaIndex Integration Plan

## Background
We're updating MagicScroll to use LlamaIndex's document store and property graph store capabilities properly. The initial work on ms_index.py is complete - it now correctly uses:

- RedisDocumentStore for document storage 
- Neo4jPropertyGraphStore for property graph operations
- StorageContext to coordinate between them

## Files To Update

### /scramble/magicscroll/ms_store.py
- Replace direct Redis operations with LlamaIndex's RedisDocumentStore
- Update interface to match LlamaIndex document store patterns
- Ensure proper transaction and batch operation support
- Consider removal if functionality fully handled by LlamaIndex's RedisDocumentStore

### /scramble/magicscroll/ms_entry.py  
- Review and update entry types to work smoothly with LlamaIndex Document objects
- Ensure metadata handling aligns with LlamaIndex patterns
- Update any ChromaDB-specific code (like sanitize_metadata_for_chroma) to be storage-agnostic
- Consider adding helper methods for LlamaIndex document conversion

## Implementation Notes
- Keep our strong typing and data validation
- Maintain backwards compatibility where possible
- Consider phasing out ms_store.py if RedisDocumentStore covers all needs
- Ensure proper error handling and logging remain robust
- Keep Neo4j-specific methods for complex graph operations

## Files Already Updated
- /scramble/magicscroll/ms_index.py - Now properly uses LlamaIndex stores and StorageContext

This migration will give us better integration with LlamaIndex's ecosytem while maintaining our app-specific functionality.
