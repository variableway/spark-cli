# Git Sub Commands

## Task 1: Support Personal Account Batch Clone

- Given a Personal account for example: jackwener
- Clone all the repos for this account into one folder
- modify clone-org to support both org and personal account, and change the clone-org command to batch-clone or something relavent
- modify all the documents about clone-org 

## Status: ✅ Completed

### Changes Made

1. **internal/github/org.go**
   - Added `GetUserRepos()` function to fetch user repositories
   - Added `DetectAccountType()` function to auto-detect if account is org or user
   - Added `GetReposForAccount()` function that auto-detects type and fetches repos
   - Renamed `ParseOrgFromURL()` to `ParseAccountFromURL()`

2. **cmd/git/batch_clone.go** (new file)
   - Created new `batch-clone` command replacing `clone-org`
   - Auto-detects account type (organization or user)
   - Shows account type in output

3. **cmd/git/clone_org.go** (deleted)
   - Removed old `clone-org` command

4. **cmd/git/update_org_status.go**
   - Updated to use `ParseAccountFromURL()` instead of `ParseOrgFromURL()`

5. **Updated Documentation**
   - `CLAUDE.md` - Updated command hierarchy
   - `AGENTS.md` - Updated command reference
   - `docs/Agents.md` - Updated command reference
   - `README.md` - Updated command table
   - `docs/README.md` - Updated command table
   - `docs/index.md` - Updated command table
   - `cmd/git/git.go` - Updated command description
   - `docs/usage/git.md` - Updated usage documentation
   - `docs/features/git.md` - Updated feature documentation
   - `docs/spec/git.md` - Updated command specification
   - `docs/quick-start/getting-started.md` - Updated quick start guide

### Usage Examples

```bash
# Clone organization repositories
spark git batch-clone variableway -o ./repos

# Clone user repositories
spark git batch-clone jackwener -o ./repos

# Using full URL
spark git batch-clone https://github.com/jackwener

# With options
spark git batch-clone variableway --ssh --include spark --exclude test -o ./output
```

## Task 2: add a folder of github repo into current folder as git submodule

- given  a folder with multiple github repo folders
- given a foler is a github repo
- add this one github repo or all the github repos in the folder as git submodule,and don't change any folder structure to do so

please check the ```spark git create``` command to do so, add or modify sub command, change the create command for create mono repo is more reasonable for me.
1 . Change create command into add command, the add current folder as submodule or submodules without cloning existing repo
2. Sometimes for research purpose,you may clone a lot of repo to one folder, use add may more reasonable than create a whole new repo then to clone add the existing repo as submodules.

Verification:
1. in folder [innate-next-mono](../../../../innate-next-mono),there is folder frontend-tpl contains a lot of github repo folders
2. add all these github repo as submodule

## Status: ✅ Completed

### Changes Made

1. **cmd/git/mono.go** (new file)
   - Created `mono` subcommand group under `git`
   - Houses `add` and `sync` subcommands

2. **cmd/git/mono_add.go** (new file)
   - `spark git mono add` command - adds existing git repos as submodules
   - Scans directory for git repos, adds them without re-cloning
   - Supports `-p/--path` flag to specify target directory

3. **cmd/git/create.go** (deleted)
   - Removed old `create` command, replaced by `mono add`

4. **cmd/git/sync.go**
   - Moved from `spark git sync` to `spark git mono sync`

5. **internal/mono/adder.go** (new file)
   - `AddExistingReposAsSubmodules()` - adds repos as submodules without cloning
   - Moves `.git` dirs to `.git/modules/`, creates `.git` files with gitdir references
   - `FindSubRepos()` - discovers git repos in a directory

6. **cmd/git/git.go**
   - Updated command description to reflect new hierarchy

### Usage Examples

```bash
# Add all git repos in current directory as submodules
spark git mono add

# Add repos from a specific directory
spark git mono add -p /path/to/folder

# Sync submodules after adding
spark git mono sync /path/to/mono-repo
``` 