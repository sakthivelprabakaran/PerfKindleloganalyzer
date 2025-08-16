import os
import subprocess
import sys

def run_git_command(command):
    """Run a git command and return the output"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=os.getcwd())
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Error: {result.stderr.strip()}"
    except Exception as e:
        return f"Exception: {str(e)}"

def main():
    print("Current directory:", os.getcwd())
    
    # Check if we're in a git repository
    git_dir_check = run_git_command("git rev-parse --is-inside-work-tree 2>/dev/null")
    if "true" in git_dir_check.lower():
        print("✓ Already in a git repository")
    else:
        print("✗ Not in a git repository, initializing...")
        init_result = run_git_command("git init")
        print(init_result)
        
        # Set main branch
        run_git_command("git checkout -b main")
    
    # Check status
    print("\nGit Status:")
    status = run_git_command("git status --porcelain")
    print(status if status else "No changes to commit")
    
    # Add all files
    print("\nAdding all files...")
    add_result = run_git_command("git add .")
    print(add_result)
    
    # Check if there are changes to commit
    status_after_add = run_git_command("git status --porcelain")
    if status_after_add:
        print("\nCommitting changes...")
        commit_result = run_git_command('git commit -m "Initial commit of Kindle Log Analyzer"')
        print(commit_result)
    else:
        print("\nNo changes to commit")
    
    print("\nGit log:")
    log_result = run_git_command("git log --oneline -5")
    print(log_result if log_result else "No commits yet")
    
    print("\nTo push to a remote repository:")
    print("1. Create a repository on GitHub/GitLab/Bitbucket")
    print("2. Add the remote: git remote add origin <repository-url>")
    print("3. Push the changes: git push -u origin main")

if __name__ == "__main__":
    main()