# Scramble Project Structure

```
scramble/
├── core/                      # Shared fundamental functionality
│   ├── storage/              # Storage and context management
│   │   ├── llama_store.py    # LlamaIndex integration
│   │   └── context.py        # Context management basics
│   ├── chat/                 # Base chat capabilities
│   │   └── base.py           # Shared chat functionality
│   └── utils/                # Common utilities
│
├── llm_harness/              # LiteLLM integration module
│   ├── clients/              # Model-specific clients
│   └── utils/                # LLM utilities
│
├── ramble/                   # CLI chat client
│   ├── cli/                  # Command line interface
│   └── handlers/             # Message handling
│
└── living_room/              # Artistic web chat project
    ├── backend/              # FastAPI server
    │   ├── app.py           # Main FastAPI setup
    │   ├── routes.py        # WebSocket routing
    │   └── handlers.py      # Message handling
    └── frontend/            # React frontend
        └── src/
            └── App.js       # Terminal-style chat UI

Key Features by Component:

## Core
- LlamaIndex document/conversation storage
- Context management and retrieval
- Shared chat functionality
- Common utilities

## LLM Harness
- LiteLLM integration
- Model-agnostic interfaces
- Easy model switching

## Ramble
- CLI chat interface
- Context-aware conversations
- Document management

## Living Room
- Minimalist chat interface
- Identity exploration
- Community interaction
- WebSocket-based real-time chat
```
