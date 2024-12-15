# Interface Cluster Architecture

```graphviz
digraph G {
    rankdir=TB;
    node [shape=box, style=rounded];
    
    // Interface base components
    subgraph cluster_base {
        label = "Interface Base Layer";
        style = filled;
        color = lightgrey;
        
        interface_base [label="ScrambleInterface\ncore/interface.py"];
        ui_components [label="UIComponents\nui/components.py"];
        env_manager [label="EnvironmentManager\ncore/environment.py"];
    }
    
    // Tool exposure layer
    subgraph cluster_tools {
        label = "Interface Tools";
        style = filled;
        color = lightyellow;
        
        tool_manager [label="InterfaceToolManager\nui/tools.py"];
        local_tools [label="LocalTools\nui/local_tools/"];
        mcp_adapter [label="MCPAdapter\nui/mcp.py"];
    }
    
    // Concrete interfaces
    subgraph cluster_apps {
        label = "Applications";
        style = filled;
        color = lightblue;
        
        ramblemaxx [label="RambleMAXX\nramblemaxx/app.py"];
        ramble [label="Ramble\nramble/app.py"];
        living_room [label="LivingRoom\nliving_room/app.py"];
    }
    
    // Shared relationships
    interface_base -> ui_components;
    interface_base -> env_manager;
    interface_base -> tool_manager;
    
    tool_manager -> local_tools;
    tool_manager -> mcp_adapter;
    
    // App inheritance and usage
    ramblemaxx -> interface_base;
    ramble -> interface_base;
    living_room -> interface_base;
    
    // Tool exposure
    ramblemaxx -> local_tools [label="exposes"];
    ramble -> local_tools [label="exposes"];
    living_room -> local_tools [label="exposes"];
    
    env_manager -> local_tools [label="configures"];
    
    // Invisible edges for layout
    {rank=same; ramblemaxx; ramble; living_room}
}
```

Key aspects of this design:

1. **ScrambleInterface + UIComponents**: Base layer that provides:
   - Common display functions (time, prompts, etc)
   - Basic input handling
   - Core scroll interactions
   - Standardized component interfaces

2. **EnvironmentManager**: 
   - Manages interface capabilities configuration
   - Provides capability discovery for models
   - Handles environment variables and settings
   - Maps available UI components to tools

3. **InterfaceToolManager**:
   - Handles tool registration from interfaces
   - Manages tool lifecycles
   - Provides tool discovery
   - Abstracts MCP vs local implementation

4. Each interface app can:
   - Inherit common functionality
   - Expose specific capabilities as tools
   - Configure its environment
   - Extend base components

This design allows for:
- Code reuse through the base layer
- Flexible capability exposure
- Clean separation between interface and tools
- Easy porting of features between interfaces

Shall we refine this further? We could:
1. Detail specific UIComponents we want to share
2. Design the capability discovery system
3. Look at the tool registration flow
4. Something else?