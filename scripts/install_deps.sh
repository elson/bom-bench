#!/bin/bash

# Only run in remote environments
if [ "$CLAUDE_CODE_REMOTE" != "true" ]; then
  exit 0
fi

MISE_VERSION="2025.12.1"

# Check if mise is already installed
if command -v mise &> /dev/null; then
  echo "✓ mise is already installed at $(command -v mise)"
  mise --version
  exit 0
fi

echo "Installing mise via npm..."

# Check if npm is available
if ! command -v npm &> /dev/null; then
  echo "✗ npm not found, cannot install mise"
  exit 1
fi

# Install mise using npm
if npm install -g @jdxcode/mise@$MISE_VERSION; then
  echo "✓ Successfully installed mise $MISE_VERSION via npm"
else
  echo "✗ npm installation failed"
  exit 1
fi

# Activate mise for bash (only add if not already present)
if ! grep -q 'mise activate bash' ~/.bashrc 2>/dev/null; then
  echo 'eval "$(mise activate bash)"' >> ~/.bashrc
  echo "✓ Added mise activation to ~/.bashrc"
  echo "⚠️  Please restart your terminal session for mise to be activated"
else
  echo "✓ mise activation already configured in ~/.bashrc"
fi

echo "✓ mise installation complete!"
