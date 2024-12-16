# Magic Scroll Architecture

```mermaid
classDiagram
    class MagicScroll {
        +index: MSIndexBase
        +write_conversation()
        +write_document()
        +write_image()
        +write_code()
        +remember()
        +recall()
        +forget()
        +recall_recent()
        +recall_thread()
        +summarize()
    }

    class MSIndexBase {
        <<abstract>>
        +add_entry()*
        +get_entry()*
        +delete_entry()*
        +search()*
        +get_recent()*
        +get_chain()*
    }

    class LlamaIndexImpl {
        -storage_path: Path
        -embed_model
        -service_context
        -storage_context
        -index
        +add_entry()
        +get_entry()
        +delete_entry()
        +search()
        +get_recent()
        +get_chain()
    }

    class MSEntry {
        +id: str
        +content: str
        +entry_type: EntryType
        +metadata: Dict
        +created_at: datetime
        +updated_at: datetime
        +parent_id: Optional[str]
        +to_dict()
        +from_dict()
    }

    class MSConversation {
        +speaker_count
    }

    class MSDocument {
        +title: str
        +uri: str
    }

    class MSImage {
        +caption: str
        +uri: str
    }

    class MSCode {
        +language: str
    }

    class EntryType {
        <<enumeration>>
        CONVERSATION
        DOCUMENT
        IMAGE
        CODE
        TOOL_CALL
    }

    MagicScroll --> MSIndexBase : uses
    MSIndexBase <|-- LlamaIndexImpl : implements
    MSEntry --> EntryType : has
    MSEntry <|-- MSConversation : extends
    MSEntry <|-- MSDocument : extends
    MSEntry <|-- MSImage : extends
    MSEntry <|-- MSCode : extends
    MagicScroll --> MSEntry : manages
```

```mermaid
graph TB
    %% Styling
    classDef scroll fill:#f9d71c,stroke:#d4b80f,color:#000
    classDef index fill:#a2d2ff,stroke:#7b9ef0,color:#000
    classDef entry fill:#b5e48c,stroke:#76c893,color:#000
    classDef store fill:#ffd6ff,stroke:#e9c3e9,color:#000

    %% The Scroll Level
    MagicScroll[THE Magic Scroll]:::scroll
    
    %% Index Level
    MSIndexBase[MSIndexBase]:::index
    LlamaIndex[LlamaIndex Implementation]:::index
    
    %% Entry Types
    Conversation[Conversations]:::entry
    Document[Documents]:::entry
    Image[Images]:::entry
    Code[Code Snippets]:::entry
    
    %% Storage Level
    VectorStore[Vector Store]:::store
    DocStore[Document Store]:::store
    
    %% Relationships
    MagicScroll --> MSIndexBase
    MSIndexBase --> LlamaIndex
    LlamaIndex --> VectorStore
    LlamaIndex --> DocStore
    
    MagicScroll --> |manages| Conversation
    MagicScroll --> |manages| Document
    MagicScroll --> |manages| Image
    MagicScroll --> |manages| Code
```

This visualization shows:
1. The hierarchical relationship between components
2. The abstract index interface and its implementation
3. The various types of entries
4. How everything connects through the MagicScroll

The class diagram shows the detailed structure, while the flow diagram shows the conceptual organization. Both diagrams together give a complete picture of THE scroll that rules them all! 📜✨

Would you like me to:
1. Add more detail to any part of the diagrams?
2. Create additional diagrams showing other aspects?
3. Add sequence diagrams for specific operations?