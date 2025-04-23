#!/bin/bash
# Start the ramble application with Magic Scroll enabled

# Check if CI mode is requested
CI_MODE=0
for arg in "$@"; do
  if [ "$arg" == "--ci-mode" ]; then
    CI_MODE=1
    echo "Running in CI mode"
  fi
done

# Make sure Redis is running
docker-compose up -d redis

# Wait a moment for Redis to fully start
sleep 2

# Set Redis environment
source tools/redis_env.sh

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
  echo "Virtual environment activated"
fi

# Start ramble, with CI mode if requested
if [ $CI_MODE -eq 1 ]; then
  python -m ramble.app --ci-mode
else
  python -m ramble.app
fi