#!/bin/bash

# Check if a commit message was provided
if [ -z "$1" ]; then
  echo "Usage: ./push_to_github.sh \"Commit message\""
  echo "Using default message: 'Auto update'"
  COMMIT_MSG="Auto update"
else
  COMMIT_MSG="$1"
fi

echo "Adding changes..."
git add .

echo "Committing changes..."
git commit -m "$COMMIT_MSG"

echo "Pushing to GitHub..."
git push origin main

echo "Done!"
