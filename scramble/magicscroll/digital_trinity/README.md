# Digital Trinity: FIPA ACL Integration

The Digital Trinity module adds standardized messaging between models using the FIPA ACL (Agent Communication Language) standard. This enhancement provides a foundation for more sophisticated multi-model conversations.

## Key Components

### FIPA ACL Integration

- **FIPAACLMessage**: Core message format based on the FIPA standard
- **FIPAACLDatabase**: SQLite storage for FIPA messages and conversations
- **MessageAdapter**: Converters between FIPA and model-specific formats

### Enhanced Coordinator

- **EnhancedCoordinator**: Extension of the base Coordinator with FIPA support
- **EnhancedConversation**: Conversation manager that supports FIPA messages
- **FIPACoordinatorBridge**: Bridge between the Coordinator and FIPA system

### FIPA-Enhanced Models

- **FIPAModelSupport**: Protocol for models that support FIPA messaging
- **FIPAModelMixin**: Base implementation of FIPA support for models
- **FIPAAnthropicModel**: Anthropic model with FIPA support
- **FIPAOllamaModel**: Ollama model with FIPA support

## Usage

The enhanced components are designed to be backward compatible with the existing system. You can use them as direct replacements:

```python
# Create enhanced coordinator
from scramble.coordinator.enhanced_coordinator import EnhancedCoordinator
coordinator = await EnhancedCoordinator.create()

# Create FIPA-enhanced models
from scramble.model.model_factory import ModelFactory
granite_model = await ModelFactory.create_model(
    model_name="granite-sparse:2b", 
    model_type="ollama",
    use_fipa=True
)
coordinator.active_models["Granite"] = granite_model

# Process messages as normal
response = await coordinator.process_message("Hello, could you introduce yourself please?")
```

## Benefits of FIPA Integration

1. **Standardized Communication**: Common message format across different model types
2. **Rich Metadata**: FIPA messages include performatives, conversation IDs, etc.
3. **Conversation Threading**: Support for threaded replies and conversation tracking
4. **Interoperability**: Makes it easier to integrate new model types and providers
5. **Future Extensibility**: Foundation for more complex agent interactions

## FIPA ACL Message Structure

Each FIPA message includes:

- **Performative**: The type of communicative act (REQUEST, INFORM, etc.)
- **Sender**: The identity of the sender
- **Receiver**: The intended recipient(s)
- **Content**: The actual message content
- **Conversation ID**: The ID of the conversation the message belongs to
- **Reply-to**: The entity to which replies should be sent
- **In-reply-to**: Reference to a previous message's ID

## Implementation Details

The integration maintains compatibility with existing components while adding new capabilities:

- The EnhancedCoordinator works with both FIPA-enabled and standard models
- Models without FIPA support continue to work normally
- FIPA messages are stored in both the MagicScroll system and a dedicated SQLite database
- Message adapters handle conversion between different formats

## Future Directions

1. Add support for more advanced FIPA performatives (PROPOSE, QUERY_IF, etc.)
2. Implement specialized agent roles with different capabilities
3. Add support for more model providers
4. Enhance the conversation threading capabilities
5. Develop a visualization tool for FIPA conversations
