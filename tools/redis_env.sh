#!/bin/bash
# Set environment variables for Redis Docker connection

# Check container status
container_id=$(docker ps -q -f name=magicscroll-redis)
if [ -z "$container_id" ]; then
  echo "WARNING: Redis container not running!"
  echo "Run 'docker-compose up -d redis' to start it"
  exit 1
fi

# Determine the best way to connect to Redis
CONTAINER_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' magicscroll-redis)

# Check if we can connect to Redis through container IP
if redis-cli -h $CONTAINER_IP ping >/dev/null 2>&1; then
  # Use container IP if accessible
  export REDIS_HOST=$CONTAINER_IP
  export REDIS_PORT=6379
  export REDIS_CONTAINER_MODE=0
  echo "Redis connection environment set using container IP:"
else
  # Fall back to localhost and use the container via docker exec
  export REDIS_HOST="localhost"
  export REDIS_PORT=6379
  export REDIS_CONTAINER_MODE=1
  echo "Redis connection environment set using container execution:"
fi

echo "REDIS_HOST=$REDIS_HOST"
echo "REDIS_PORT=$REDIS_PORT"
echo "REDIS_CONTAINER_MODE=$REDIS_CONTAINER_MODE"
echo "Run 'source tools/redis_env.sh' before starting ramble"

echo "Redis container running with ID: $container_id"

# Get info about modules (always use docker exec for this check)
modules=$(docker exec magicscroll-redis redis-cli MODULE LIST | grep -E 'name|search')
if [[ $modules == *"search"* ]]; then
  echo "✅ Redis search module loaded and available"
else
  echo "⚠️ Redis search module not detected - vector search may not work"
fi