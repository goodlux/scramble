# FIPA Integration for Scramble

This document outlines the implementation of the FIPA (Foundation for Intelligent Physical Agents) ACL (Agent Communication Language) integration for the Scramble multi-model chat system.

## Overview

The FIPA integration enhances Scramble's existing architecture with standardized communication protocols and improves message history management. This implementation preserves backward compatibility while providing a foundation for more sophisticated multi-model interactions.

## Key Components

### 1. FIPA Message Storage (MSFIPAStorage)

Located in `scramble/magicscroll/ms_fipa.py`, this component handles the persistent storage of FIPA messages using SQLite:

- `fipa_conversations` table: Stores metadata about conversations
- `fipa_messages` table: Stores individual messages with their metadata

The storage provides methods for:
- Creating conversations
- Saving messages
- Retrieving messages (with filtering options)
- Closing conversations

### 2. Message Type Classification

Located in `scramble/coordinator/active_conversation.py`, the `MessageType` enum defines different types of messages:

- `PERMANENT`: Messages that should be saved to long-term memory
- `EPHEMERAL`: Temporary messages (like memory injections) that aren't stored
- `COORDINATION`: System messages for coordinating between models

### 3. Enhanced ActiveConversation

The `ActiveConversation` class has been updated to:

- Track FIPA conversation IDs
- Support message type classification
- Provide methods for adding different types of messages
- Filter messages based on their type when formatting for storage

### 4. MagicScroll FIPA Integration

The `MagicScroll` class now provides methods to interact with FIPA storage:

- Creating FIPA conversations
- Saving FIPA messages
- Retrieving FIPA conversations
- Saving filtered FIPA conversations to long-term storage

### 5. Coordinator Integration

The `Coordinator` class has been updated to:
- Create FIPA conversations when starting new sessions
- Save messages to FIPA storage during conversations
- Use FIPA for saving conversations to long-term storage

### 6. Model Hierarchy Clarification

The model hierarchy has been clarified:

- `ModelBase`: Base class for all models (LLM or otherwise)
- `LLMModelBase`: Specific implementation for text LLMs

## Message Flow

1. User sends a message to the Coordinator
2. Coordinator adds message to ActiveConversation
3. Message is saved to FIPA storage with appropriate metadata
4. If memory injection is needed, EPHEMERAL messages are added
5. Model responses are also saved to FIPA storage
6. When conversation ends, only PERMANENT messages are saved to long-term storage

## Testing

You can test the FIPA integration using the test script at `tests/test_fipa_integration.py`:

```bash
python tests/test_fipa_integration.py
```

## Future Improvements

1. Add more sophisticated message filtering based on content
2. Implement threaded conversation support
3. Add support for more FIPA performatives (currently only INFORM is used)
4. Enhance the coordinator to utilize FIPA for model coordination
5. Add tools for browsing and analyzing FIPA conversation history
