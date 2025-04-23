# Graph Search & Entity Extraction in Scramble

## Current Architecture

Scramble uses a multi-component storage system:
1. **Neo4j Property Graph**: Stores document chunks, embeddings, and relationships between entities
2. **Redis**: Document store for complete conversations
3. LlamaIndex: Provides abstractions for graph operations and document processing

## Graph Search Operations

Document-Node Relationships:
- Documents are split into chunks (nodes labeled `__Node__`)
- Each chunk can have entity nodes (labeled `__Entity__`)
- Relationships are maintained via `MENTIONS` relationships
- The structure allows tracing from documents → chunks → entities

Current Implementation:
- Uses `ImplicitPathExtractor` for basic relationship extraction
- No LLM-based entity extraction currently
- Search operations happen during chat for context
- Full document processing happens at conversation end

## Current Investigation (Jan 2025)

### Issue Being Investigated

Currently investigating entity extraction issues in `/Users/rob/repos/scramble/scramble/magicscroll/ms_index.py`. Key findings:

1. **Node Types**: Only seeing `Node` and `Chunk` types in Neo4j, despite the LLM successfully extracting entities and relationships.

2. **Library Usage Questions**:
   - The LLM (granite3.1-dense:2b) appears to be successfully extracting entities from text
   - However, these entities aren't being properly stored in Neo4j
   - Unclear if this is due to:
     a) Incorrect parameter configuration in LlamaIndex
     b) A fundamental issue with the graph store code
     c) Limitations of the local model

3. **Configuration Being Tested**:
   ```python
   kg_extractor = DynamicLLMPathExtractor(
       llm=llm,
       max_triplets_per_chunk=20,
       num_workers=4,
       allowed_entity_types=None,  # Let LLM decide types
       allowed_relation_types=None, # Let LLM decide relations
       allowed_relation_props=[],
       allowed_entity_props=[],
   )
   ```

4. **Current Debug Focus**:
   - Testing whether removing constraints on entity/relation types improves extraction
   - Comparing different extractors (SimpleLLMPathExtractor vs DynamicLLMPathExtractor)
   - Investigating if chunk creation is overriding entity type information

## Performance Findings

1. **Model Deployment**:
   - Local Ollama significantly faster than Docker deployment
   - Currently using granite3.1-dense:2b model
   - Search operations appear functional but need better visibility into results

2. **Storage Operations**:
   - Node creation during conversation save requires adequate chunk size
   - Graph operations are async and don't impact chat performance
   - Neo4j Community Edition limited to 4 CPU cores for PropertyGraph

## Future Improvements

### Phase 1: Performance Optimization
- [ ] Clean up Docker configuration
- [ ] Remove unused Chroma components
- [ ] Investigate local model performance optimization
   - GPU configuration
   - Model quantization options
   - Batch processing strategies

### Phase 2: Enhanced Entity Extraction
- [ ] Debug current entity extraction issues
   - Test different LlamaIndex configurations
   - Try different extractors
   - Add more logging around extraction process
- [ ] Implement working LLM-based entity extraction using local model
- [ ] Options:
   - Post-conversation processing only
   - Background processing during quiet periods
   - Selective processing for important conversations
- [ ] Add debugging output for search results
   - Log what context is being found
   - Show relationship paths being used
   - Monitor entity extraction quality

### Key Decisions Made:
1. Keep chat fast by doing minimal processing during conversation
2. Move complex graph operations to post-conversation phase
3. Use local LLM deployment for better latency
4. Maintain Neo4j for rich relationship modeling despite CPU limits

## LlamaIndex Graph Components

The PropertyGraphIndex provides several key extractors:
1. `SimpleLLMPathExtractor`: Uses LLM to find (entity1, relation, entity2) triplets
2. `ImplicitPathExtractor`: Uses existing node relationships
3. `DynamicLLMPathExtractor`: Allows specification of entity and relation types
4. `SchemaLLMPathExtractor`: Enforces strict schema for entities and relationships

When implementing LLM-based extraction:
- Can use local models (might be slower but cost-effective)
- Process in background to maintain performance
- Consider selective processing based on conversation importance
- May need to tune batch sizes and chunk processing for optimal performance

## To Be Investigated:
1. Whether current entity extraction issues are configuration or code-based
2. Optimal model size/type for entity extraction
3. Performance impact of different extraction strategies
4. Best practices for Neo4j community edition optimization
5. Trade-offs between extraction quality and processing speed