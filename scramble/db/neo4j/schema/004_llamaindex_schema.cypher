// LlamaIndex Integration Schema
CREATE CONSTRAINT llamaindex_entity_id IF NOT EXISTS FOR (e:__Entity__) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT llamaindex_node_id IF NOT EXISTS FOR (e:__Node__) REQUIRE e.id IS UNIQUE;

// Optional - add indexes for better performance
CREATE INDEX llamaindex_entity_name IF NOT EXISTS FOR (e:__Entity__) ON (e.name);
CREATE INDEX llamaindex_node_text IF NOT EXISTS FOR (e:__Node__) ON (e.text);