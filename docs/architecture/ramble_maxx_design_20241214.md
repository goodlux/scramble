Yes! Let's document what we've figured out! Here's a design doc:

# Ramble Design Document

## Core Concepts

### The Scroll
- Central timeline of all interactions
- User-owned conversation history
- Multi-model support
- Continuous context across models
- Natural model addressing ("Claude, can you...")

### Tool System
1. **Local Tools**
   - UI/Interface controls
   - Code panel management
   - View controls
   - Can be exposed via MCP

2. **Server Tools**
   - MCP-compatible
   - Discoverable
   - Dynamically loadable

3. **Dynamic Tools**
   - Model-created tools
   - Safely sandboxed
   - Runtime generated

## Project Structure
scramble/ ├── core/ │ ├── scroll.py # Scroll implementation │ └── scroll_manager.py # Manages scroll + models ├── tools/ │ ├── base.py # Tool base classes │ ├── registry.py # Tool management │ └── mcp.py # MCP integration ├── ramble/ # CLI interface └── ramblemaxx/ # Enhanced Textual interface ├── app.py # Main Textual app ├── tools/ │ ├── ui.py # UI-specific tools │ ├── code.py # Code panel tools │ └── viz.py # Visualization tools └── styles/ └── maxx.tcss # Textual CSS


## Interfaces

### RambleMaxx Layout
┌─────────────────────────────────────────────────────────┐ │ RambleMaxx │ ├─────────┬───────────────────────────────┬───────────────┤ │ Models │ The Scroll │ Side Panel │ │ │ │ │ │ [x] C3 │ You: Claude, can you help │ [Code] │ │ [x] GPT4│ with this Python code... │ def foo(): │ │ [ ] Mis │ │ pass │ │ │ Claude: Here's an approach... │ │ │ Filter │ │ [Doc View] │ │ > Date │ You: GPT-4, what do you │ # Header │ │ > Topic │ think about Claude's... │ │ │ │ │ │ └─────────┴───────────────────────────────┴───────────────┘





### Tool Integration
- Tools can be local or MCP-served
- UI elements can be controlled via tools
- Models can interact with UI through MCP
- Dynamic tool creation supported

### Model Integration
- Multiple models in single scroll
- Natural language model selection
- Context sharing between models
- Tool availability per model

## Next Steps
1. Implement basic RambleMaxx interface
2. Add core UI tools
3. Integrate with Scroll
4. Add MCP support
5. Implement server tool discovery
6. Add dynamic tool support