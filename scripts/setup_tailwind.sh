#!/bin/bash
# Setup script for Tailwind CSS CLI

echo "=== PYQ Analyzer - Tailwind CSS Setup ==="

# Detect OS and architecture
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

# Map architecture names
if [ "$ARCH" = "x86_64" ]; then
    ARCH="x64"
elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    ARCH="arm64"
elif [ "$ARCH" = "armv7l" ]; then
    ARCH="armv7"
fi

# Determine download URL based on OS and architecture
# Using v3.4.17 for compatibility with the current configuration
VERSION="v3.4.17"
BINARY_NAME="tailwindcss-${OS}-${ARCH}"
DOWNLOAD_URL="https://github.com/tailwindlabs/tailwindcss/releases/download/${VERSION}/${BINARY_NAME}"

echo "Detected OS: ${OS}"
echo "Detected Architecture: ${ARCH}"
echo "Binary name: ${BINARY_NAME}"

# Check if binary already exists
if [ -f "${BINARY_NAME}" ]; then
    echo "Tailwind CSS CLI already exists: ${BINARY_NAME}"
    echo "Making it executable..."
    chmod +x "${BINARY_NAME}"
    echo "✓ Setup complete!"
    exit 0
fi

# Download the binary
echo "Downloading Tailwind CSS CLI from ${DOWNLOAD_URL}..."
if command -v curl &> /dev/null; then
    curl -sL "${DOWNLOAD_URL}" -o "${BINARY_NAME}"
elif command -v wget &> /dev/null; then
    wget -q "${DOWNLOAD_URL}" -O "${BINARY_NAME}"
else
    echo "Error: Neither curl nor wget is available. Please install one of them."
    exit 1
fi

# Check if download was successful
if [ ! -f "${BINARY_NAME}" ]; then
    echo "Error: Failed to download Tailwind CSS CLI"
    exit 1
fi

# Make it executable
chmod +x "${BINARY_NAME}"

echo ""
echo "=== Setup Complete ==="
echo "Tailwind CSS CLI downloaded: ${BINARY_NAME}"
echo "You can now build CSS with:"
echo "  ./${BINARY_NAME} -i static/css/input.css -o static/css/output.css"
echo ""
echo "To watch for changes during development:"
echo "  ./${BINARY_NAME} -i static/css/input.css -o static/css/output.css --watch"
