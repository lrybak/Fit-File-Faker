#!/usr/bin/env bash
# Release automation script for Fit File Faker
# Usage: ./release.sh <version> [release-message]
# Example: ./release.sh 2.0.1 "Fix changelog generation and dependencies"

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
error() {
    echo -e "${RED}Error: $1${NC}" >&2
    exit 1
}

info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if version is provided
if [ -z "$1" ]; then
    error "Version number required. Usage: ./release.sh <version> [release-message]"
fi

VERSION="$1"
RELEASE_MESSAGE="${2:-Release v${VERSION}}"

# Validate version format (should be X.Y.Z)
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    error "Invalid version format. Expected: X.Y.Z (e.g., 2.0.1)"
fi

# Check if git working directory is clean
if ! git diff-index --quiet HEAD --; then
    warn "Working directory has uncommitted changes."
    echo -e "${YELLOW}Uncommitted files:${NC}"
    git status --short
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if we're on main branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    warn "You are on branch '$CURRENT_BRANCH', not 'main'."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if tag already exists
if git rev-parse "v${VERSION}" >/dev/null 2>&1; then
    error "Tag v${VERSION} already exists. Use a different version."
fi

info "Preparing release v${VERSION}..."
echo

# Step 1: Update version in pyproject.toml
info "Updating version in pyproject.toml..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/^version = \".*\"/version = \"${VERSION}\"/" pyproject.toml
else
    # Linux
    sed -i "s/^version = \".*\"/version = \"${VERSION}\"/" pyproject.toml
fi
success "Version updated to ${VERSION}"

# Step 2: Show the diff
info "Changes to pyproject.toml:"
git diff pyproject.toml

# Step 3: Commit version change
echo
read -p "Commit this version change? (Y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    git add pyproject.toml
    git commit -m "chore: bump version to ${VERSION}"
    success "Version change committed"
else
    error "Release cancelled by user"
fi

# Step 4: Create annotated tag
info "Creating annotated tag v${VERSION}..."
echo
echo -e "${BLUE}Release message:${NC}"
echo "  ${RELEASE_MESSAGE}"
echo
read -p "Create tag with this message? (Y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    git tag -a "v${VERSION}" -m "${RELEASE_MESSAGE}"
    success "Tag v${VERSION} created"
else
    error "Release cancelled by user"
fi

# Step 5: Push to remote
echo
info "Ready to push to origin..."
echo "  - Commits on branch: ${CURRENT_BRANCH}"
echo "  - Tag: v${VERSION}"
echo
read -p "Push to origin? (Y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    git push origin "$CURRENT_BRANCH"
    git push origin "v${VERSION}"
    success "Pushed to origin"
else
    warn "Changes committed locally but not pushed."
    warn "To push manually, run:"
    echo "  git push origin ${CURRENT_BRANCH}"
    echo "  git push origin v${VERSION}"
    exit 0
fi

# Step 6: Create draft GitHub release (if gh CLI is available)
echo
if command -v gh &> /dev/null; then
    info "Creating draft GitHub release..."
    read -p "Create draft release on GitHub? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        # Generate changelog for this version
        info "Generating release notes..."
        
        # Create release notes with the tag message and auto-generated notes
        if gh release create "v${VERSION}" \
            --draft \
            --title "v${VERSION}" \
            --notes "${RELEASE_MESSAGE}

---

**Full Changelog**: See the [changelog](https://jat255.github.io/Fit-File-Faker/changelog/) for detailed changes.
" \
            --verify-tag; then
            success "Draft release created on GitHub"
            echo
            info "Review and publish: https://github.com/jat255/Fit-File-Faker/releases/tag/v${VERSION}"
        else
            warn "Failed to create GitHub release. You can create it manually."
        fi
    fi
else
    warn "GitHub CLI (gh) not found. Skipping draft release creation."
    info "Install gh: https://cli.github.com/"
fi

# Done!
echo
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Release v${VERSION} completed successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo
info "Next steps:"
echo "  1. Monitor GitHub Actions: https://github.com/jat255/Fit-File-Faker/actions"
echo "  2. Verify PyPI release: https://pypi.org/project/fit-file-faker/"
echo "  3. Review/publish draft release: https://github.com/jat255/Fit-File-Faker/releases"
echo "  4. Review docs: https://jat255.github.io/Fit-File-Faker/"
echo
