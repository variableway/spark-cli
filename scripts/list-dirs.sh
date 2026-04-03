#!/bin/bash
# Example script: List directories with details
# Usage: spark script run list-dirs

echo "📁 Directory listing:"
echo "====================="
ls -la | grep "^d"
echo ""
echo "📄 Files:"
echo "========"
ls -la | grep "^-"
