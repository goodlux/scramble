#!/bin/bash

# Neo4j Schema Initialization Script 🔮
# Waits for Neo4j to be ready and applies schema files

echo "🔄 Waiting for Neo4j to be ready..."

# Wait for Neo4j to be healthy
while ! docker-compose exec neo4j wget --no-verbose --tries=1 --spider localhost:7474 2>/dev/null
do
    echo "⏳ Neo4j is starting up..."
    sleep 5
done

echo "✨ Neo4j is ready!"

# Get password from environment or use default
NEO4J_PASSWORD=${NEO4J_PASSWORD:-scR4Mble#Graph!}

echo "🔮 Applying schema files..."

# Apply schema files in order
for schema in scramble/db/neo4j/schema/*.cypher; do
    echo "📝 Applying schema: $(basename $schema)"
    cat $schema | docker-compose exec -T neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD"
done

echo "✅ Schema initialization complete!"