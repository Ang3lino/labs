# Git

```bash
alias g="git"
```

## Branch

```bash
git checkout -b <branch>                  # Create + switch
git checkout --track origin/<branch>      # Switch to remote branch
git branch -a                             # List all branches
git stash && git checkout <branch> && git stash pop  # Switch with uncommitted work
```

## Work

```bash
git status
git diff
git diff --staged
git add .
git commit -m "feat: <message>"
```

## Push / Sync

```bash
git push -u origin <branch>     # First push
git push                        # Subsequent pushes
git push --force-with-lease     # Safe force push
git fetch --prune               # Clean stale remotes
```

## Merge

```bash
git checkout main
git pull origin main
git merge <branch>              # Resolve conflicts manually, then: git add . && git commit
git push origin main
```

## Cleanup

```bash
git branch -d <branch>              # Delete merged branch
git branch -D <branch>              # Force delete unmerged
git push origin --delete <branch>   # Delete remote branch
```

## PR (gh CLI)

```bash
gh pr create --title "feat: <title>" --body "Description"
gh pr status
```
