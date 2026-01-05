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

  # Try method 3: npm
  if ! command -v mise &> /dev/null; then
    echo "Attempting to install mise via npm..."

    # Check if npm is available
    if command -v npm &> /dev/null; then
      if npm install -g @jdxcode/mise 2>/dev/null; then
        echo "✓ Successfully installed mise via npm"
      else
        echo "✗ npm installation failed"
      fi
    else
      echo "✗ npm not found, skipping npm method"
    fi
  fi

  # Try method 4: cargo-binstall
  if ! command -v mise &> /dev/null; then
    echo "Attempting to install mise via cargo-binstall..."

    # Check if cargo is available
    if command -v cargo &> /dev/null; then
      echo "Found cargo, installing cargo-binstall..."
      if cargo install cargo-binstall 2>/dev/null; then
        echo "✓ cargo-binstall installed"

        # Now use cargo-binstall to install mise
        if cargo binstall -y mise 2>/dev/null; then
          echo "✓ Successfully installed mise via cargo-binstall"
        else
          echo "✗ cargo-binstall mise installation failed"
        fi
      else
        echo "✗ Failed to install cargo-binstall"
      fi
    else
      echo "✗ cargo not found, skipping cargo-binstall method"
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
  echo "  1. Install via npm: npm install -g @jdxcode/mise"
  echo "  2. Pre-install mise in the Docker image/container"
  echo "  3. Whitelist mise.jdx.dev and github.com in the proxy"
  echo "  4. Manually copy the mise binary to /usr/local/bin/mise"
  echo ""
  exit 1
fi
