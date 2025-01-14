# Progressive Document Simplification (ProgDS) Notes

## Reference
"Progressive Document-level Text Simplification via Large Language Models"  
Fang et al., January 2024  
https://arxiv.org/pdf/2501.03857

## Overview
ProgDS is a hierarchical approach to understanding and transforming long documents through multiple stages of analysis:

1. Discourse-level simplification
   - Overall document structure
   - Topic organization
   - High-level coherence

2. Topic-level simplification
   - Paragraph analysis
   - Content organization
   - Flow management

3. Lexical-level simplification
   - Vocabulary simplification
   - Expression replacement
   - Readability improvements

## Key Insights
- Document simplification requires hierarchical understanding
- Can't treat simplification as just summarization
- Progress from high-level structure to detailed lexical choices
- Maintains document coherence through structured approach

## Implementation Considerations for Scramble

### Architecture Potential
```
scramble/
└── simplifier/
    ├── stages/
    │   ├── discourse_simplifier.py
    │   ├── topic_simplifier.py
    │   └── lexical_simplifier.py
    ├── pipeline.py
    └── neo4j_manager.py
```

### Data Storage Options
- Neo4j: Document structure and relationships
- ChromaDB: Semantic similarity and patterns
- Redis: Intermediate processing states

### Token Usage
- Heavy LLM usage in original implementation
- Potential to use local LLM (granite-sparse:2b) for initial processing
- Pass structured results to Claude for higher-level analysis

## Potential Use Cases

### Massive Document Processing
- Entire books
- Academic theses
- Technical documentation
- Legal documents

### GitHub Repository Analysis
Interesting potential application treating entire repos as "documents":
- Discourse-level → Repository structure
- Topic-level → Files/modules
- Lexical-level → Code patterns

### Implementation Strategy
Could be implemented as an "ephemeral subsystem":
1. Generate detailed understanding on demand
2. Maintain in memory while needed
3. Option to persist or discard analysis
4. Regenerate when needed

## Future Considerations
- Integration with existing Scramble architecture
- Balance between local and cloud LLM processing
- Storage strategies for analysis results
- Optimization for specific use cases like code repositories

## Notes
- Current priority is fixing existing bugs in Scramble
- Need to identify compelling use cases beyond current capabilities
- GitHub repo analysis could be killer feature
- Consider as future enhancement after core stability