# Data Archive Ingestion

A research proposal for expanding Scramble's capabilities to ingest and understand personal data archives.

## Overview

Most major platforms (Google, Facebook, Twitter, etc.) allow users to download their complete data history. However, these "data dumps" are often difficult to work with - they're like having all your possessions dumped on your lawn rather than carefully moved into a new house. This project aims to make these personal data archives actually useful by integrating them into Scramble's knowledge graph.

## Phase 1: Basic Email Ingestion

Start with email as a proof of concept, since:
- Email has well-defined standards (MBOX format)
- Clear conversation structure
- Rich metadata (timestamps, participants, threads)
- Common patterns across different providers

### Implementation Steps:
1. Create MBOX parser in MagicScroll
2. Define basic Neo4j schema for emails:
   ```cypher
   (Message)-[:PART_OF]->(Thread)
   (Message)-[:SENT_BY]->(Person)
   (Message)-[:SENT_TO]->(Person)
   (Thread)-[:HAS_LABEL]->(Label)
   ```
3. Import pipeline:
   - Parse MBOX
   - Extract core entities (messages, people, threads)
   - Build relationships
   - Store in Neo4j

## Phase 2: Dynamic Schema Discovery

Expand to handle arbitrary data types using LLMs and LlamaParse for intelligent data understanding.

### Key Components:

1. **Flexible Data Parser**
   - Use LlamaParse for initial document structure understanding
   - Handle multimodal content (text, tables, images)
   - Extract semantic relationships

2. **Schema Discovery System**
   - LLM-enhanced schema analysis
   - Generate Neo4j schemas on the fly
   - Learn from successful patterns
   - Version control for schemas as they evolve

3. **Data Type Registry**
   - Known format definitions
   - Schema version history
   - Transformation rules
   - Validation requirements

### Architecture:

```python
scramble/magicscroll/data_fabric/
├── core/
│   ├── registry.py      # Plugin/handler registration
│   ├── transformer.py   # Data transformation engine
│   └── schema.py        # Dynamic schema management
├── handlers/            # Data source handlers
│   ├── base.py         
│   └── plugins/         # Plugin handlers live here
└── mapping/            # Data mapping definitions
    └── schemas/        # YAML/JSON schema definitions
```

### Workflow:

1. User provides data archive
2. System analyzes sample data using LlamaParse
3. LLM suggests appropriate Neo4j schema
4. Schema is versioned and stored
5. Data is transformed and imported
6. Schema and transformation rules are refined based on success

### Challenges to Consider:

1. **Schema Evolution**
   - How to handle schema changes
   - Migration strategies
   - Version control

2. **Data Quality**
   - Validation rules
   - Error handling
   - Data cleaning

3. **Performance**
   - Batch processing
   - Incremental updates
   - Large dataset handling

4. **Privacy & Security**
   - Data sensitivity levels
   - Access control
   - Encryption needs

## Future Possibilities

1. **Cross-Platform Integration**
   - Linking data across different platforms
   - Building comprehensive user timelines
   - Identifying platform-spanning relationships

2. **Semantic Understanding**
   - Topic extraction
   - Entity recognition
   - Sentiment analysis
   - Event detection

3. **Interactive Refinement**
   - User feedback on schema decisions
   - Manual corrections
   - Learning from corrections

## Next Steps

1. Implement basic email ingestion
2. Test with sample Google Takeout data
3. Evaluate LlamaParse integration
4. Design schema versioning system
5. Build basic plugin architecture

## Open Questions

1. How do we handle conflicts between different data sources?
2. What's the right balance between automation and manual configuration?
3. How do we maintain performance with large datasets?
4. How should we version and migrate schemas as they evolve?