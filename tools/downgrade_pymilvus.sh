#!/bin/bash
# Script to downgrade PyMilvus to a more stable version for pymilvus-lite

# Activate the virtual environment
source .venv/bin/activate

# Uninstall current PyMilvus
echo "Uninstalling current PyMilvus version..."
pip uninstall -y pymilvus
pip uninstall -y milvus-lite

# Install the stable version with lite support
echo "Installing PyMilvus 2.4.0 with milvus-lite support..."
pip install pymilvus==2.4.0
pip install milvus-lite==2.4.12  # Latest compatible version with PyMilvus 2.4.0

echo "PyMilvus downgraded successfully!"
echo "Current versions:"
python -c "import pymilvus; print(f'PyMilvus version: {pymilvus.__version__}')"
python -c "import milvus; from milvus import MilvusLiteClient; print(f'Milvus-lite module is available')"