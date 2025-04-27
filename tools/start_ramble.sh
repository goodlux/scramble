#!/bin/bash
# Start the ramble application with SQLite-based MagicScroll

# Check if CI mode is requested
CI_MODE=0
for arg in "$@"; do
  if [ "$arg" == "--ci-mode" ]; then
    CI_MODE=1
    echo "Running in CI mode"
  fi
done

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
  echo "Virtual environment activated"
fi

# Make sure ~/.scramble directory exists
mkdir -p ~/.scramble

echo "Starting ramble with SQLite-based MagicScroll..."

# Start ramble, with CI mode if requested
if [ $CI_MODE -eq 1 ]; then
  python -m ramble.app --ci-mode
else
  python -m ramble.app
fi
