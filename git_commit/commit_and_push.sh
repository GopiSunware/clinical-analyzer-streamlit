#!/usr/bin/env bash
set -euo pipefail

# Commit all changes with an auto-generated or provided message and push.
# Priority for PAT (safest first):
#  1) GH_PAT env var
#  2) git_commit/PRIVATE_GITHUB_PAT.txt (if present)
#  3) Built-in fallback below

# Intentionally blank — populate GH_PAT in your shell instead of baking tokens here.
FALLBACK_PAT=""
PAT="${GH_PAT:-}"
if [ -z "$PAT" ] && [ -f "git_commit/PRIVATE_GITHUB_PAT.txt" ]; then
  PAT="$(cat git_commit/PRIVATE_GITHUB_PAT.txt)"
fi
if [ -z "$PAT" ]; then
  PAT="$FALLBACK_PAT"
fi

# Determine commit message
if [ "$#" -gt 0 ]; then
  MSG="$*"
else
  # Generate a concise message from staged/unstaged changes
  CHANGES=$(git status --porcelain)
  if [ -z "$CHANGES" ]; then
    echo "No changes to commit."; exit 0
  fi
  COUNT=$(echo "$CHANGES" | wc -l | tr -d ' ')
  PREVIEW=$(echo "$CHANGES" | awk '{print $2}' | head -n 5 | tr '\n' ' ')
  MSG="auto: update ${COUNT} files — ${PREVIEW}"
fi

# Stage, commit, and push
git add -A
if git diff --cached --quiet; then
  echo "No staged changes. Nothing to commit."; exit 0
fi
git commit -m "$MSG"

BR=$(git rev-parse --abbrev-ref HEAD)
REMOTE="https://x-access-token:${PAT}@github.com/GopiSunware/SmartBuild.git"
echo "Pushing '${BR}' to SmartBuild..."
git push -u "$REMOTE" "$BR"
echo "Done."
