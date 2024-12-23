# Storage Architecture
Date: November 5, 2024

## Overview
The storage system manages conversation contexts, compressed content, and identity information using a multi-tiered approach.

### Storage Tiers

1. Active Memory
- Current conversation context
- Recently accessed contexts
- Active identity information
- Location: RAM

2. Recent Storage
- Recent conversations
- Active conversation chains
- Compressed contexts
- Location: ~/.ramble/store/recent/

3. Archive Storage
- Historical conversations
- Archived contexts
- Compressed long-term storage
- Location: ~/.ramble/store/archive/

### Data Organization

```
~/.ramble/
├── store/
│   ├── recent/          # Recent contexts
│   │   ├── contexts/    # Context files
│   │   └── chains/      # Chain relationships
│   ├── archive/         # Historical data
│   │   ├── contexts/    # Archived contexts
│   │   └── chains/      # Historical chains
│   └── identity/        # Identity data
├── tmp/                 # Temporary files
└── config/             # Configuration
```

## Implementation Details

### Context Storage
- Use .ctx format for context files
- Implement progressive compression
- Maintain relationship links
- Support context pruning

### Identity Storage
- Separate identity storage
- Encrypted sensitive data
- Version control for changes
- Backup and restore support

### Chain Management
- Track conversation threads
- Maintain relationship graphs
- Support chain merging
- Enable context retrieval
