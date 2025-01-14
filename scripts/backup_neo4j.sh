#!/bin/bash

# Create backup directory if it doesn't exist
BACKUP_DIR="./backups/neo4j"
mkdir -p "$BACKUP_DIR"

# Get current timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup
echo "Creating Neo4j backup..."
docker run --rm \
    --volumes-from $(docker compose ps -q neo4j) \
    -v $(pwd)/$BACKUP_DIR:/backup \
    debian:latest \
    tar czf /backup/neo4j_backup_$TIMESTAMP.tar.gz /data /logs

echo "Backup created at $BACKUP_DIR/neo4j_backup_$TIMESTAMP.tar.gz"