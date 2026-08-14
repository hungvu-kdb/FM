# GIT.md

Record of the git commands used to replace the entire contents of
`https://github.com/hungvu-kdb/FM.git` (branch `main`) with the local `d:\Random\Pic` folder,
discarding all previous repo history and files.

Remote tip before the operation: `cf3d265e2c3a194d02dd330bf9022dad6917387d`

## 1. Inspect the remote without cloning

```bash
# show default branch (HEAD symref) and every branch tip
git ls-remote --symref https://github.com/hungvu-kdb/FM.git

# just the ref list, used to capture the pre-overwrite tip SHA
git ls-remote https://github.com/hungvu-kdb/FM.git
```

## 2. Check local environment

```bash
git --version
git config --global user.name
git config --global user.email
git config --global credential.helper
```

## 3. Initialize the local folder as a repo and attach the remote

```bash
git init -b main                                              # new repo, initial branch named main
git remote add origin https://github.com/hungvu-kdb/FM.git    # register the target repo
```

Notes:
- `git init` is safe to re-run; it prints `Reinitialized existing Git repository` and
  ignores `-b` when the repo already exists.
- `git remote add` fails with `error: remote origin already exists` if it is already set.
  Use `git remote set-url origin <url>` to change it instead.

## 4. Stage everything and create a history-free commit

```bash
git add -A                                                    # stage all files, respecting .gitignore
git commit -m "Replace repo contents with Pic frame-analysis project"
```

Because the repo was created fresh with `git init`, this commit has **no parent**, so none of
the old repo history is carried over.

If a repo with existing history is already checked out, create the parentless commit explicitly:

```bash
git checkout --orphan main    # new branch with no parent commit
git rm -rf .                 # clear the index and working tree of tracked files
git add -A
git commit -m "Initial commit"
```

## 5. Untrack files that should have been ignored

A `.gitignore` was added covering `__pycache__/`, `.vscode/`, `bin/`, `obj/`, `node_modules/`, etc.
Files already staged are not removed by `.gitignore`, so they were untracked explicitly.

```bash
# --cached removes from the index only; files stay on disk
git rm -r --cached .vscode "MVP2/__pycache__" "__pycache__"

git add -A
git commit --amend -m "Replace repo contents with Pic frame-analysis project"
```

`--amend` rewrites the most recent commit. Only safe here because the commit had not been pushed.

## 6. Verify before pushing

```bash
git rev-parse --abbrev-ref HEAD          # current branch name
git rev-parse HEAD                       # current commit SHA
git remote -v                            # fetch/push URLs
git log --oneline -n 10                  # recent commits
git log --pretty="%h parents=[%P] %s"    # confirm the commit has no parent
git status --short                       # working tree should be empty
git ls-tree -r --name-only HEAD          # exact file list inside the commit
```

## 7. Overwrite the remote branch

```bash
git push --force-with-lease=main:cf3d265e2c3a194d02dd330bf9022dad6917387d origin main
```

- A plain `git push` is rejected here: the local and remote histories share no common commit
  (`non-fast-forward` / `unrelated histories`).
- `--force-with-lease=<ref>:<expected-sha>` overwrites the branch **only** if the remote is still
  at that exact SHA. If someone else pushed in the meantime the push aborts instead of destroying
  their work. Prefer this over the blunt `--force` / `-f`.
- If `main` is a protected branch in the GitHub repo settings, the force push is refused. Relax
  the protection rule temporarily, or push to a new branch and merge via pull request.

## 8. Confirm the remote matches

```bash
git ls-remote https://github.com/hungvu-kdb/FM.git    # tip SHA should equal local HEAD
git rev-parse HEAD
```

## Undo / recovery reference

```bash
# save the current remote tip to a backup branch BEFORE overwriting (not used here)
git push origin cf3d265e2c3a194d02dd330bf9022dad6917387d:refs/heads/backup-main

# save a local safety ref before rewriting a branch
git branch backup/main main

# discard local changes and match the remote exactly (for other clones after the force push)
git fetch origin
git reset --hard origin/main
```

## Commands deliberately avoided

- `git push --force` without `--with-lease`: silently overwrites concurrent pushes.
- `git clean -fdx`: would have deleted untracked and ignored files from disk. Untracking with
  `git rm --cached` keeps the local files intact.
- `git commit --amend` on already-pushed commits: forces history rewrites on collaborators.
