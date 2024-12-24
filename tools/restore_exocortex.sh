#!/bin/bash

# ExoCortex Restore Script 🧠🔄
# Restores from a backup archive

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <backup_archive.tar.gz>"
    exit 1
fi

BACKUP_ARCHIVE=$1

if [ ! -f "$BACKUP_ARCHIVE" ]; then
    echo "❌ Backup archive not found: $BACKUP_ARCHIVE"
    exit 1
fi

echo "📦 Restoring ExoCortex from: $BACKUP_ARCHIVE"

# Stop services
docker-compose down

# Extract backup
tmp_dir=$(mktemp -d)
tar xzf "$BACKUP_ARCHIVE" -C "$tmp_dir"
backup_dir=$(ls "$tmp_dir")

# Restore volumes
echo "🧠 Restoring Neo4j data..."
docker run --rm -v scramble_neo4j_data:/target -v $(pwd)/${tmp_dir}/${backup_dir}:/backup alpine sh -c "cd /target && tar xzf /backup/neo4j_data.tar.gz"

echo "🔮 Restoring ChromaDB data..."
docker run --rm -v scramble_chroma_data:/target -v $(pwd)/${tmp_dir}/${backup_dir}:/backup alpine sh -c "cd /target && tar xzf /backup/chroma_data.tar.gz"

echo "📝 Restoring Redis data..."
docker run --rm -v scramble_redis_data:/target -v $(pwd)/${tmp_dir}/${backup_dir}:/backup alpine sh -c "cd /target && tar xzf /backup/redis_data.tar.gz"

# Cleanup
rm -rf "$tmp_dir"

# Start services
docker-compose up -d

echo "✨ Restore complete!"
echo "🚀 ExoCortex services restarted"