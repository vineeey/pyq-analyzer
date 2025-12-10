# Tailwind CSS Binary Setup

## Overview
This project uses the Tailwind CSS standalone CLI binary (`tailwindcss-linux-x64`) for building CSS without requiring Node.js as a runtime dependency.

## Binary Management

### Location
The binary should be placed in the project root directory: `tailwindcss-linux-x64`

### Git Tracking
**Important**: The Tailwind CSS binary is **NOT tracked in Git**. It is excluded via `.gitignore` to:
- Reduce repository size (the binary is ~42MB)
- Avoid committing build tools to version control
- Follow best practices (similar to excluding `node_modules/`)

### Setup for New Developers

If you clone this repository and the binary is missing, download it:

```bash
# Download the Tailwind CSS standalone binary for Linux x64
curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64

# Make it executable
chmod +x tailwindcss-linux-x64

# Verify it works
./tailwindcss-linux-x64 --help
```

For other platforms:
- **macOS Intel**: `tailwindcss-macos-x64`
- **macOS ARM**: `tailwindcss-macos-arm64`
- **Windows**: `tailwindcss-windows-x64.exe`

Download from: https://github.com/tailwindlabs/tailwindcss/releases/latest

## Usage

Build CSS:
```bash
./tailwindcss-linux-x64 -i static/css/input.css -o static/css/output.css
```

Watch mode (for development):
```bash
./tailwindcss-linux-x64 -i static/css/input.css -o static/css/output.css --watch
```

## Why Not Use npm/yarn?

We use the standalone binary to:
1. **Reduce dependencies**: No need to install Node.js, npm, or hundreds of npm packages
2. **Faster setup**: Single binary download vs full npm install
3. **Simpler deployment**: Just copy the binary to production
4. **Lower disk usage**: ~42MB binary vs ~200MB+ node_modules

## Troubleshooting

### Binary Not Found
```bash
# Check if binary exists
ls -lh tailwindcss-linux-x64

# If missing, download it (see Setup section above)
```

### Permission Denied
```bash
# Make sure the binary is executable
chmod +x tailwindcss-linux-x64
```

### Wrong Platform
If you're not on Linux x64, download the appropriate binary for your platform from the Tailwind CSS releases page.

## References
- [Tailwind CSS Standalone CLI](https://tailwindcss.com/blog/standalone-cli)
- [Releases](https://github.com/tailwindlabs/tailwindcss/releases)
