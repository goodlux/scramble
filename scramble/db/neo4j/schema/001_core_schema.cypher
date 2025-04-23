// Core Schema - Shared Knowledge Structure

// Node Constraints
CREATE CONSTRAINT conversation_id IF NOT EXISTS FOR (c:Conversation) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT message_id IF NOT EXISTS FOR (m:Message) REQUIRE m.id IS UNIQUE;
CREATE CONSTRAINT topic_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE;
CREATE CONSTRAINT model_id IF NOT EXISTS FOR (m:Model) REQUIRE m.model_id IS UNIQUE;
CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE;

// Node Indexes
CREATE INDEX message_timestamp IF NOT EXISTS FOR (m:Message) ON (m.timestamp);
CREATE INDEX conversation_timestamp IF NOT EXISTS FOR (c:Conversation) ON (c.timestamp);
CREATE INDEX topic_search IF NOT EXISTS FOR (t:Topic) ON (t.name, t.description);
CREATE INDEX model_search IF NOT EXISTS FOR (m:Model) ON (m.model_name);

// Schema Comments
/*
Core Node Properties:

Conversation {
  id: string,              // UUID
  timestamp: datetime,     // When started
  metadata: map,           // Flexible metadata
  vector_id: string,       // ChromaDB reference
  type: string            // Conversation type (e.g., single-model, multi-model)
}

Message {
  id: string,              // UUID
  content: string,         // The actual message content
  timestamp: datetime,     // When created
  metadata: map,           // Flexible metadata
  vector_id: string,       // ChromaDB reference
  type: string            // Message type (e.g., command, query, response)
}

Topic {
  name: string,            // Unique topic identifier
  description: string,     // Topic description
  metadata: map           // Additional topic metadata
}

Model {
  model_id: string,       // Unique model identifier
  model_name: string,     // Display name
  model_type: string,     // Type (e.g., claude, local)
  capabilities: list      // Model capabilities
}

User {
  id: string,            // User identifier
  name: string,          // Display name
  metadata: map         // User preferences/settings
}

Core Relationships:
:PART_OF              // Message -> Conversation, shows which messages belong to which conversation
:NEXT_IN_SEQUENCE     // Message -> Message, temporal sequence within a conversation
:SENT_BY              // Message -> User/Model, who sent the message
:ADDRESSED_TO         // Message -> User/Model, intended recipient of the message
:DISCUSSES            // Message -> Topic, links messages to topics
:REFERENCES           // Message -> Message/Document/etc, cross-references to other content
:RELATED_TO          // Topic -> Topic, shows relationships between topics

Example Patterns:

1. Create a new message in a conversation:
MATCH (c:Conversation {id: $convId})
MATCH (sender:User {id: $senderId})
MATCH (recipient:Model {id: $recipientId})
CREATE (m:Message {
  id: $msgId,
  content: $content,
  timestamp: datetime(),
  type: 'query'
})
CREATE (m)-[:PART_OF]->(c)
CREATE (m)-[:SENT_BY]->(sender)
CREATE (m)-[:ADDRESSED_TO]->(recipient)
RETURN m

2. Get conversation thread with sender/recipient info:
MATCH (c:Conversation {id: $convId})<-[:PART_OF]-(m:Message)
MATCH (m)-[:SENT_BY]->(sender)
MATCH (m)-[:ADDRESSED_TO]->(recipient)
RETURN m, sender, recipient
ORDER BY m.timestamp

3. Find all messages between specific participants:
MATCH (sender:User {id: $userId})
MATCH (model:Model {id: $modelId})
MATCH (m:Message)
WHERE (m)-[:SENT_BY]->(sender) AND (m)-[:ADDRESSED_TO]->(model)
   OR (m)-[:SENT_BY]->(model) AND (m)-[:ADDRESSED_TO]->(sender)
RETURN m
ORDER BY m.timestamp

4. Find conversations involving specific topics:
MATCH (t:Topic {name: $topicName})
MATCH (m:Message)-[:DISCUSSES]->(t)
MATCH (c:Conversation)<-[:PART_OF]-(m)
RETURN DISTINCT c

5. Get message chain with context:
MATCH (m:Message {id: $msgId})
MATCH (m)-[:PART_OF]->(c:Conversation)
MATCH (c)<-[:PART_OF]-(related:Message)
OPTIONAL MATCH (related)-[:DISCUSSES]->(t:Topic)
OPTIONAL MATCH (related)-[:REFERENCES]->(ref)
RETURN related, t, ref
ORDER BY related.timestamp
*/

// TODO(living-room): Additional room-specific constraints and relationships