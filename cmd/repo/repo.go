package repo

import (
	"github.com/spf13/cobra"
)

var RepoCmd = &cobra.Command{
	Use:   "repo",
	Short: "Manage GitHub repositories via a registry file (not submodules)",
	Long: `Manage a directory of GitHub repositories using a registry file instead of
git submodules.

Commands:
- scan:  scan a folder and write its repositories to registry_<folder>.yaml
- clone: clone repositories from a registry file into the folder directory
- list:  list repositories declared in a registry file`,
}

func init() {
}
