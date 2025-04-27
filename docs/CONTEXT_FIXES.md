# Context Handling Fixes

This document details fixes to the vector search context handling in the scRAMble project.

## Problem Summary

The system correctly retrieved relevant conversations from vector search, but the LLM wasn't properly using this context in its responses. This was due to several issues in how the context was structured and passed to the LLM models.

## Key Changes

### 1. Message Enricher Improvements

In `scramble/coordinator/message_enricher.py`:

- Improved extraction of conversation IDs from search results
- Enhanced timestamp handling to properly format dates
- Added more robust extraction of conversation content
- Improved topic matching for more relevant context
- Added better debugging logs

### 2. LLM Model Handling

In both `ollama_llm_model.py` and `anthropic_llm_model.py`:

- Updated message preparation to properly parse "PREVIOUS CONVERSATIONS REFERENCE:" sections
- Split enriched context into separate system messages for better context awareness
- Fixed handling of complex nested conversation structures
- Added more detailed logs about message counts and system messages

### 3. Coordinator Changes

In `coordinator.py`:

- Improved context building to handle multiple context sources
- Fixed handling when combining conversation context with vector search results
- Enhanced logging of the final context

## Testing

You can verify that the fixes are working by:

1. Looking for logs showing the proper conversation IDs and timestamps
2. Checking the log line `Sending X messages to Ollama, including Y system messages`
3. Observing whether the model's responses incorporate information from the context

## Debugging Tips

If issues persist with context handling:

1. Check the logs for warnings about "Insufficient conversation extract"
2. Look for specific conversation IDs and timestamps in the context
3. Examine the actual content being extracted from conversations
4. Check how many system messages are being sent to the model

## Known Limitations

- The system requires properly structured vector search results
- Timestamps may still be missing if not found in any of the checked locations
- Models with limited system message capabilities may not fully utilize the context

## Update: Direct Context Embedding

After testing, we discovered that some models (like Ollama's granite-sparse:2b) don't properly process system messages. We've updated the context handling to embed the context directly in the user message instead, with explicit instructions for the model to use this information.

Key changes:

1. Instead of splitting context into system messages, we now format it as part of the user message with clear instructions
2. The format now explicitly tells the model "IMPORTANT - Your response must reference the following context information:"
3. This should force models to acknowledge and use the context even if they don't fully support system messages
4. We then ask the model "Based on this context, please respond to: [original query]"

This approach ensures the model can't ignore the context by making it part of the primary user message instruction.
