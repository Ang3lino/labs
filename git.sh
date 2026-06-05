#!/bin/bash
set -euo pipefail

alias g="git"
# ── CONFIG ──
REMOTE="origin"
MAIN="main"

# ── BRANCH ──
git checkout -b "$1"          # Create + switch
git checkout --track "$REMOTE/$1"   # Switch to remote branch
git branch -a                 # List all branches
git stash && git checkout "$1" && git stash pop  # Switch with uncommitted work

# ── WORK ──
git status
git diff
git diff --staged
git add .
git commit -m "feat: $1"

# ── PUSH / SYNC ──
git push -u "$REMOTE" "$1"    # First push
git push                      # Subsequent pushes
git push --force-with-lease   # Safe force push
git fetch --prune             # Clean stale remotes

# ── MERGE ──
git checkout "$MAIN"
git pull "$REMOTE" "$MAIN"
git merge "$1"                # Resolve conflicts manually, then: git add . && git commit
git push "$REMOTE" "$MAIN"

# ── CLEANUP ──
git branch -d "$1"            # Delete merged branch
git branch -D "$1"            # Force delete unmerged
git push "$REMOTE" --delete "$1"   # Delete remote branch

# ── PR (requires gh CLI) ──
gh pr create --title "feat: $1" --body "Description"
gh pr status
