package git

import (
	"github.com/spf13/cobra"
)

var GitCmd = &cobra.Command{
	Use:   "git",
	Short: "Git repository management commands",
	Long: `Git commands for managing multiple repositories.

This includes:
- update: Update multiple git repositories
- clone: Clone a GitHub repository via gh repo clone (SSH by default)
- init: Initialize a git repo and create a GitHub remote
- submodule: Add local repos or URLs as git submodules
- sync: Sync all submodules to the latest versions
- gitcode: Add Gitcode as remote
- config: Configure git user for repository
- url: Get repository remote URL
- batch-clone: Clone all repos from a GitHub organization or user
- issues: Create GitHub issues from markdown files or tasks
- push-all: Commit and push all changes in repositories`,
}

func init() {
}
