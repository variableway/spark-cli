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
- create: Create a mono repo with submodules
- sync: Sync submodules in a mono repo
- gitcode: Add Gitcode as remote
- config: Configure git user for repository
- url: Get repository remote URL
- batch-clone: Clone all repos from a GitHub organization or user`,
}

func init() {
}
