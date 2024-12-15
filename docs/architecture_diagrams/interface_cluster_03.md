# Interface Architecture - InterfaceBase 

```graphviz
digraph G {
    rankdir=TB;
    node [shape=box, style=rounded];
    
    // Core interface base
    subgraph cluster_base {
        label = "InterfaceBase\ncore/interface.py";
        style = filled;
        color = lightblue;
        
        // Core functions
        display [label="Display\n- output(content)\n- error(msg)\n- status(msg)"];
        input [label="Input\n- get_input()\n- handle_input()\n- handle_commands()"];
        capabilities [label="Capabilities\n- has_sidebar\n- has_code_view\n- get_features()"];
        commands [label="Commands\n- :h (help)\n- :q (quit)\n- :c (clear)\n- :d (debug)"];
    }
    
    // Apps
    ramblemaxx [label="RambleMAXX\nramblemaxx/app.py"];
    ramble [label="Ramble\nramble/app.py"];
    
    // System connection
    scroll_manager [label="ScrollManager\ncore/scroll_manager.py"];
    
    // Relationships
    ramblemaxx -> display;
    ramblemaxx -> input;
    ramblemaxx -> capabilities;
    ramblemaxx -> commands;
    
    ramble -> display;
    ramble -> input;
    ramble -> capabilities;
    ramble -> commands;
    
    display -> scroll_manager;
    input -> scroll_manager;
    
    // Layout
    {rank=same; ramblemaxx; ramble}
}
```

Common functionality I see between ramble and rambleMAXX:

1. **Display Functions**
   - Showing chat output
   - Displaying errors/status
   - Formatting timestamps
   - Showing prompts
   - Clear screen capability

2. **Input Handling**
   - Getting user input
   - Command processing
   - Input validation
   - History management

3. **Capability Reporting**
   - Available features (sidebar, code view, etc)
   - UI constraints
   - Tool availability 
   - Display capabilities

4. **Command Standards**
   - Help (:h)
   - Quit (:q)
   - Clear (:c)
   - Debug toggle (:d)
   - Theme cycling (in rambleMAXX but could be conditional)

5. **Common Patterns** 
   - Async operation
   - Error handling
   - Graceful shutdown
   - Configuration loading
   - Status/feedback to user

The key insight seems to be that InterfaceBase isn't managing multiple apps, but rather providing a foundational set of capabilities that any scramble interface needs, while letting each interface implement those capabilities in its own way.

Does this better capture what InterfaceBase should be? Are there other common patterns between the interfaces that I missed?