#!/usr/bin/env bash
# Build documentation locally with changelog generation
# This mirrors the GitHub Actions workflow for local testing
#
# Usage:
#   ./build_docs.sh          # Generate changelog and build docs
#   ./build_docs.sh serve    # Generate changelog and serve docs with live reload
#   ./build_docs.sh --bump   # Build with auto-bumped version number
#   ./build_docs.sh --help   # Show help

set -e  # Exit on error

# Parse arguments
SERVE=false
if [[ "$1" == "serve" ]]; then
    SERVE=true
elif [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    echo "Usage: $0 [serve] [--bump]"
    echo ""
    echo "Build documentation locally with changelog generation."
    echo ""
    echo "Options:"
    echo "  (none)    Generate changelog for unreleased changes and build static docs"
    echo "  serve     Generate changelog and serve docs with live reload"
    echo "  --bump    Auto-calculate next version and preview release changelog"
    echo "  --help    Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0              # Build with [Unreleased] section"
    echo "  $0 --bump       # Build with auto-bumped version (e.g., v1.2.5)"
    echo "  $0 serve --bump # Serve with bumped version preview"
    exit 0
fi

echo "🔨 Building Fit File Faker documentation..."
echo ""

# Check if git-cliff is installed
if ! command -v git &> /dev/null; then
    echo "❌ Error: git-cliff is not installed"
    echo "Install it with: brew install git-cliff  (macOS)"
    echo "             or: cargo install git-cliff (Rust)"
    exit 1
fi

# Generate changelog with git-cliff
echo "📝 Generating changelog with git-cliff..."

# Check if --bump flag was passed
if [[ "$*" =~ --bump ]]; then
    NEXT_VERSION=$(git cliff --bumped-version --unreleased)
    echo "🔢 Auto-bumped version: $NEXT_VERSION (preview)"
    git cliff --verbose --output docs/changelog.md --tag "$NEXT_VERSION" --unreleased
else
    git cliff --verbose --output docs/changelog.md --unreleased
fi

# Append historical changelog
echo "📜 Appending historical changelog..."
{
    echo ""
    echo "---"
    echo ""
    cat docs/.changelog_pre_1.3.0.md
} >> docs/changelog.md

echo "✅ Changelog generated: docs/changelog.md"
echo ""

# Check if mkdocs is installed
if ! command -v uv run mkdocs &> /dev/null; then
    echo "❌ Error: mkdocs not found"
    echo "Install with: uv sync --group docs"
    exit 1
fi

# Build or serve based on option
if [ "$SERVE" = true ]; then
    echo "🌐 Starting mkdocs development server..."
    echo "📍 Documentation will be available at: http://127.0.0.1:8000"
    echo ""
    echo "Press Ctrl+C to stop the server"
    echo ""
    uv run mkdocs serve
else
    echo "📚 Building documentation with mkdocs..."
    uv run mkdocs build
    echo ""
    echo "✅ Documentation built to: site/"
    echo ""
    echo "💡 To serve locally with live reload, run: $0 serve"
fi
