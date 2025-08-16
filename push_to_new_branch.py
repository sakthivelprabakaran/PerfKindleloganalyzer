#!/usr/bin/env python3
"""
Script to push Kindle Log Analyzer code to a new branch
"""

import subprocess
import sys
import os

def run_command(command):
    """Run a shell command and return the output"""
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command '{command}': {e.stderr}")
        return None

def main():
    # Change to the KindleLogAnalyzer directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("Current directory:", os.getcwd())
    
    # Check current branch
    current_branch = run_command("git rev-parse --abbrev-ref HEAD")
    if current_branch:
        print(f"Current branch: {current_branch}")
    
    # Check if we're in a git repository
    is_git_repo = run_command("git rev-parse --is-inside-work-tree")
    if not is_git_repo or is_git_repo != "true":
        print("Initializing git repository...")
        run_command("git init")
    
    # Add all files
    print("Adding all files to git...")
    run_command("git add .")
    
    # Check if we have changes to commit
    status = run_command("git status --porcelain")
    if status:
        print("Committing changes...")
        run_command('git commit -m "Initial commit with Kindle Log Analyzer code"')
    else:
        print("No changes to commit")
    
    # Create and switch to new branch
    print("Creating and switching to new branch...")
    run_command("git checkout -b kindle-log-analyzer-branch")
    
    print("New branch created successfully!")
    print("To push to a remote repository, you can now run:")
    print("  git push -u origin kindle-log-analyzer-branch")
    
    # Check remote repositories
    remotes = run_command("git remote -v")
    if remotes:
        print("\nRemote repositories:")
        print(remotes)
    else:
        print("\nNo remote repositories configured.")
        print("To add a remote repository, run:")
        print("  git remote add origin <repository-url>")

if __name__ == "__main__":
    main()