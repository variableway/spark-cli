#!/bin/bash
# Example script: Copy template file to target directory with new name
# Usage: spark script run copy-template <new-filename>

SOURCE_FILE="tasks/example-feature.md"
TARGET_DIR="tasks/features"

if [ -z "$1" ]; then
    echo "Usage: spark script run copy-template <new-filename>"
    echo "Example: spark script run copy-template my-new-feature"
    exit 1
fi

NEW_NAME="$1"
TARGET_FILE="${TARGET_DIR}/${NEW_NAME}.md"

if [ ! -f "$SOURCE_FILE" ]; then
    echo "Error: Source file not found: $SOURCE_FILE"
    exit 1
fi

if [ -f "$TARGET_FILE" ]; then
    echo "Error: Target file already exists: $TARGET_FILE"
    exit 1
fi

cp "$SOURCE_FILE" "$TARGET_FILE"
echo "✅ Created: $TARGET_FILE"
echo "📝 Edit the file to add your task details"
