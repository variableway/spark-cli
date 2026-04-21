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
- mono: Mono repo management (add/sync submodules)
- gitcode: Add Gitcode as remote
- config: Configure git user for repository
- url: Get repository remote URL
- batch-clone: Clone all repos from a GitHub organization or user
- issues: Create GitHub issues from markdown files or tasks
- push-all: Commit and push all changes in repositories`,
}

func init() {
}
