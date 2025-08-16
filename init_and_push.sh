#!/bin/bash

# Script to push Kindle Log Analyzer code to a new branch

echo "=== Kindle Log Analyzer - Git Branch Creation Script ==="
echo

# Check if we're in the right directory
if [ ! -d "logic" ] || [ ! -d "ui" ] || [ ! -d "utils" ]; then
    echo "Error: Please run this script from the KindleLogAnalyzer directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

echo "Current directory: $(pwd)"
echo

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Initializing git repository..."
    git init
    echo
fi

# Add all files
echo "Adding all files to git..."
git add .
echo

# Check if we have changes to commit
if ! git diff --cached --quiet; then
    echo "Committing changes..."
    git commit -m "Initial commit with Kindle Log Analyzer code"
    echo
else
    echo "No changes to commit"
    echo
fi

# Create and switch to new branch
echo "Creating and switching to new branch: kindle-log-analyzer-branch"
git checkout -b kindle-log-analyzer-branch
echo

# Show current branch
echo "Current branch: $(git rev-parse --abbrev-ref HEAD)"
echo

# Show status
echo "Git status:"
git status
echo

echo "=== Script completed successfully! ==="
echo
echo "To push to a remote repository, run:"
echo "  git push -u origin kindle-log-analyzer-branch"
echo
echo "If you haven't set up a remote repository yet, run:"
echo "  git remote add origin <repository-url>"
echo "  git push -u origin kindle-log-analyzer-branch"