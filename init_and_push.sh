#!/bin/bash

# Navigate to the KindleLogAnalyzer directory
cd "$(dirname "$0")"

# Check if git is installed
if ! command -v git &> /dev/null
then
    echo "Git is not installed. Please install Git and try again."
    exit 1
fi

# Initialize git repository if it doesn't exist
if [ ! -d ".git" ]; then
    echo "Initializing new Git repository..."
    git init
    git checkout -b main
else
    echo "Git repository already exists."
fi

# Add all files
echo "Adding all files to Git..."
git add .

# Check if there are any changes to commit
if ! git diff-index --quiet HEAD --; then
    echo "Committing changes..."
    git commit -m "Initial commit of Kindle Log Analyzer"
else
    echo "No changes to commit."
fi

echo "Setup complete. To push to a remote repository, you need to:"
echo "1. Create a repository on GitHub/GitLab/Bitbucket"
echo "2. Add the remote: git remote add origin <repository-url>"
echo "3. Push the changes: git push -u origin main"