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
