#!/bin/bash

# Only run in remote environments
if [ "$CLAUDE_CODE_REMOTE" != "true" ]; then
  exit 0
fi

# Check if mise is already installed
if command -v mise &> /dev/null; then
  echo "✓ mise is already installed at $(command -v mise)"
  mise --version
  exit 0
fi

echo "Installing mise..."

# Detect architecture
ARCH=$(uname -m)
case "$ARCH" in
  x86_64)
    ARCH_SUFFIX="x64"
    ;;
  aarch64|arm64)
    ARCH_SUFFIX="arm64"
    ;;
  *)
    echo "✗ Unsupported architecture: $ARCH"
    exit 1
    ;;
esac

# Try method 1: Download from GitHub releases
echo "Attempting to install mise from GitHub releases..."
MISE_VERSION="v2024.12.16"
MISE_URL="https://github.com/jdx/mise/releases/download/${MISE_VERSION}/mise-${MISE_VERSION}-linux-${ARCH_SUFFIX}"

if curl -fsSL "${MISE_URL}" -o /tmp/mise 2>/dev/null; then
  chmod +x /tmp/mise
  mv /tmp/mise /usr/local/bin/mise
  echo "✓ Successfully installed mise from GitHub releases"
else
  echo "✗ GitHub download failed (network restrictions)"

  # Try method 2: apt repository
  echo "Attempting to install mise via apt repository..."
  if apt-get update -y >/dev/null 2>&1 && apt-get install -y curl gpg >/dev/null 2>&1; then
    install -dm 755 /etc/apt/keyrings
    if curl -fsSL https://mise.jdx.dev/gpg-key.pub -o /etc/apt/keyrings/mise-archive-keyring.pub 2>/dev/null; then
      echo "deb [signed-by=/etc/apt/keyrings/mise-archive-keyring.pub arch=${ARCH}] https://mise.jdx.dev/deb stable main" > /etc/apt/sources.list.d/mise.list
      if apt-get update -y >/dev/null 2>&1 && apt-get install -y mise >/dev/null 2>&1; then
        echo "✓ Successfully installed mise via apt"
      else
        echo "✗ apt installation failed (network restrictions)"
      fi
    else
      echo "✗ Failed to download mise GPG key (network restrictions)"
    fi
  fi
fi

# Final verification
if command -v mise &> /dev/null; then
  echo "✓ mise successfully installed at $(command -v mise)"
  mise --version

  # Activate mise for bash (only add if not already present)
  if ! grep -q 'mise activate bash' ~/.bashrc 2>/dev/null; then
    echo 'eval "$(mise activate bash)"' >> ~/.bashrc
    echo "✓ Added mise activation to ~/.bashrc"
  fi

  echo ""
  echo "✓ mise installation complete!"
  exit 0
else
  echo ""
  echo "✗ Failed to install mise"
  echo ""
  echo "This environment has network restrictions that prevent downloading mise."
  echo "Possible solutions:"
  echo "  1. Pre-install mise in the Docker image/container"
  echo "  2. Whitelist mise.jdx.dev and github.com in the proxy"
  echo "  3. Manually copy the mise binary to /usr/local/bin/mise"
  echo ""
  exit 1
fi
