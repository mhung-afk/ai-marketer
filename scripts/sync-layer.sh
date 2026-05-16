#!/bin/bash
# Sync src/common to Lambda layer directory
# This ensures the layer always has the latest code from src/common/

set -e

SRC_DIR="src/common"
LAYER_DIR="src/layers/common/python/common"

echo "Syncing $SRC_DIR to $LAYER_DIR..."

# Remove old layer files and copy fresh
rm -rf "$LAYER_DIR"
cp -r "$SRC_DIR" "$LAYER_DIR"

# Clean up pycache and pyc files
find "$LAYER_DIR" -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$LAYER_DIR" -name "*.pyc" -delete 2>/dev/null || true

echo "✓ Layer sync complete"
