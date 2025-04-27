# Context Injection Fix for Scramble

This update fixes issues with context not being properly passed to the LLM from search results and reduces logging verbosity to make debugging easier.

## Changes Made

1. **Fixed f-string formatting error** in the MessageEnricher
   - The error was causing context not to be added to the topic discussions

2. **Improved content extraction logic** in the `_add_topic_context` method
   - Now properly extracts content from various result object structures
   - Adds better logging to track content extraction

3. **Added logging configuration to reduce verbosity**
   - Created custom formatter to collapse repetitive log entries
   - Configured external libraries to use WARNING or INFO level
   - Added environment variable to toggle detailed logging

## How to Test

1. **Run with reduced logging**:
   ```bash
   SCRAMBLE_DETAILED_LOGGING=0 python -m scramble
   ```

2. **Run with detailed logging** (for debugging):
   ```bash
   SCRAMBLE_DETAILED_LOGGING=1 python -m scramble
   ```

3. **Check for context injection**:
   - Try asking questions with memory triggers like "do you remember when we talked about..."
   - Look for "ENRICHED CONTEXT BEING SENT TO MODEL" in the logs
   - You should see log entries about content being added to context

## Additional Notes

- If context extraction is working correctly, you should see log entries like:
  ```
  Content extraction: Found entry: True, Content length: 1205
  Added content to context: 1205 characters
  ```

- The logs should now be much cleaner and focus on the important information

- The formatter collapses repetitive vector search entries to reduce noise

## Rollback if Needed

If these changes cause any issues, you can revert them with:

```bash
git checkout HEAD~1 -- scramble/coordinator/message_enricher.py
git checkout HEAD~1 -- scramble/utils/logging.py
rm scramble/utils/logging_config.py
```
