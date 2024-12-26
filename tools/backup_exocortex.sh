#!/bin/bash

# ExoCortex Backup Script 🧠💼
# Creates a timestamped backup of all service data

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="exocortex_backup_${TIMESTAMP}"

echo "📦 Creating ExoCortex backup: ${BACKUP_DIR}"

# Stop services to ensure data consistency
docker-compose down

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Backup Docker volumes
echo "🧠 Backing up Neo4j data..."
docker run --rm -v scramble_neo4j_data:/source -v $(pwd)/${BACKUP_DIR}:/backup alpine tar czf /backup/neo4j_data.tar.gz -C /source ./

echo "🔮 Backing up ChromaDB data..."
docker run --rm -v scramble_chroma_data:/source -v $(pwd)/${BACKUP_DIR}:/backup alpine tar czf /backup/chroma_data.tar.gz -C /source ./

echo "📝 Backing up Redis data..."
docker run --rm -v scramble_redis_data:/source -v $(pwd)/${BACKUP_DIR}:/backup alpine tar czf /backup/redis_data.tar.gz -C /source ./

# Create metadata file
cat > "${BACKUP_DIR}/metadata.json" << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "version": "1.0",
  "services": {
    "neo4j": "5.15.0",
    "chroma": "latest",
    "redis": "7"
  }
}
EOF

# Create final archive
tar czf "${BACKUP_DIR}.tar.gz" "${BACKUP_DIR}"
rm -rf "${BACKUP_DIR}"

echo "✨ Backup complete: ${BACKUP_DIR}.tar.gz"

# Restart services
docker-compose up -d

echo "🚀 ExoCortex services restarted"