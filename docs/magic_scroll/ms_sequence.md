# Magic Scroll Sequence Diagrams

## Writing a Conversation

```mermaid
sequenceDiagram
    participant App
    participant MagicScroll
    participant MSEntry
    participant LlamaIndex
    participant Storage

    App->>MagicScroll: write_conversation(content, metadata)
    activate MagicScroll
    
    MagicScroll->>MSEntry: create MSConversation
    activate MSEntry
    MSEntry-->>MagicScroll: conversation entry
    deactivate MSEntry
    
    MagicScroll->>LlamaIndex: add_entry(entry)
    activate LlamaIndex
    
    LlamaIndex->>LlamaIndex: generate embeddings
    LlamaIndex->>Storage: store entry & vectors
    Storage-->>LlamaIndex: confirm storage
    
    LlamaIndex-->>MagicScroll: success
    deactivate LlamaIndex
    
    MagicScroll-->>App: entry_id
    deactivate MagicScroll
```

## Remembering (Searching)

```mermaid
sequenceDiagram
    participant App
    participant MagicScroll
    participant LlamaIndex
    participant VectorStore
    participant DocStore

    App->>MagicScroll: remember("previous discussions about AI")
    activate MagicScroll
    
    MagicScroll->>LlamaIndex: search(query)
    activate LlamaIndex
    
    LlamaIndex->>LlamaIndex: generate query embedding
    LlamaIndex->>VectorStore: find similar vectors
    activate VectorStore
    VectorStore-->>LlamaIndex: matching vector IDs
    deactivate VectorStore
    
    LlamaIndex->>DocStore: get entries
    activate DocStore
    DocStore-->>LlamaIndex: entry data
    deactivate DocStore
    
    LlamaIndex->>LlamaIndex: calculate scores
    LlamaIndex-->>MagicScroll: ranked results
    deactivate LlamaIndex
    
    MagicScroll-->>App: matching entries
    deactivate MagicScroll
```

## Recalling a Thread

```mermaid
sequenceDiagram
    participant App
    participant MagicScroll
    participant LlamaIndex
    participant DocStore

    App->>MagicScroll: recall_thread(entry_id)
    activate MagicScroll
    
    MagicScroll->>LlamaIndex: get_chain(entry_id)
    activate LlamaIndex
    
    loop For each parent_id
        LlamaIndex->>DocStore: get_entry(id)
        activate DocStore
        DocStore-->>LlamaIndex: entry
        deactivate DocStore
        LlamaIndex->>LlamaIndex: add to chain
    end
    
    LlamaIndex-->>MagicScroll: ordered chain
    deactivate LlamaIndex
    
    MagicScroll-->>App: conversation thread
    deactivate MagicScroll
```

## Adding a Document with Search Update

```mermaid
sequenceDiagram
    participant App
    participant MagicScroll
    participant MSEntry
    participant LlamaIndex
    participant VectorStore
    participant DocStore

    App->>MagicScroll: write_document(title, content, uri)
    activate MagicScroll
    
    MagicScroll->>MSEntry: create MSDocument
    activate MSEntry
    MSEntry-->>MagicScroll: document entry
    deactivate MSEntry
    
    MagicScroll->>LlamaIndex: add_entry(entry)
    activate LlamaIndex
    
    LlamaIndex->>LlamaIndex: chunk content
    LlamaIndex->>LlamaIndex: generate embeddings
    
    par Store Document
        LlamaIndex->>DocStore: store entry
        DocStore-->>LlamaIndex: confirm
    and Update Search
        LlamaIndex->>VectorStore: store vectors
        VectorStore-->>LlamaIndex: confirm
    end
    
    LlamaIndex-->>MagicScroll: success
    deactivate LlamaIndex
    
    MagicScroll-->>App: entry_id
    deactivate MagicScroll
```

These sequence diagrams show:
1. The flow of data between components
2. Parallel operations where applicable
3. Activation/deactivation of different components
4. The asynchronous nature of operations

Would you like to see:
1. More complex scenarios?
2. Error handling sequences?
3. Other specific operations?