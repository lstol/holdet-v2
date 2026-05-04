#!/bin/bash
# holdet-v2 — One-time local machine setup
# Run this ONCE from any folder on your machine
# After this: git pull/push just works, no tokens needed

set -e

REPO_URL="https://github.com/lstol/holdet-v2.git"
LOCAL_DIR="$HOME/Claude/holdet-v2"

echo "=== Holdet v2 Local Setup ==="

# 1. Clone or update repo
if [ -d "$LOCAL_DIR/.git" ]; then
  echo "Repo already exists — pulling latest..."
  cd "$LOCAL_DIR"
  git pull origin main
else
  echo "Cloning repo to $LOCAL_DIR..."
  mkdir -p "$HOME/Claude"
  git clone "$REPO_URL" "$LOCAL_DIR"
  cd "$LOCAL_DIR"
fi

# 2. Set identity
git config user.name "lstol"
git config user.email "lasse.stoltenberg@gmail.com"

# 3. Store credentials permanently (prompts once on next push)
git config credential.helper store

# 4. Set default branch and upstream
git branch --set-upstream-to=origin/main main 2>/dev/null || true

echo ""
echo "=== Done ==="
echo "Repo is at: $LOCAL_DIR"
echo "Next push: cd $LOCAL_DIR && git push"
echo "On first push, GitHub will ask for username + token once, then remember it."
echo ""
echo "To generate a token: https://github.com/settings/tokens"
echo "Scope needed: repo"
