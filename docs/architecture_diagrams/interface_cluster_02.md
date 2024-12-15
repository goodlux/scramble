# Interface Cluster Architecture

```graphviz
digraph G {
    rankdir=TB;
    node [shape=box, style=rounded];
    
    // Core manager
    app_manager [label="ApplicationManager\ncore/application.py", shape=component];
    
    // Interface apps
    ramblemaxx [label="RambleMAXX\nramblemaxx/app.py"];
    ramble [label="Ramble\nramble/app.py"];
    
    // Scroll system connection
    scroll_manager [label="ScrollManager\ncore/scroll_manager.py"];
    
    // Tools & Environment
    tools [label="Tools & Environment", shape=cylinder];
    
    // Core relationships
    ramblemaxx -> app_manager;
    ramble -> app_manager;
    
    app_manager -> scroll_manager;
    app_manager -> tools;
    
    // Invisible edges for layout
    {rank=same; ramblemaxx; ramble}
}
```

The ApplicationManager becomes the single source of truth for:
1. How apps talk to the scroll system
2. What capabilities are available
3. How tools are exposed
4. What UI elements exist

Everything goes through this one coordinator. Each app just needs to know how to talk to the ApplicationManager, and the ApplicationManager handles everything else.

Is this closer to what you were thinking? We could refine the name - maybe InterfaceCoordinator or UIManager might be more descriptive?