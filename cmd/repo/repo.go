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
         (categorized format: <category>/<subcategory>/<project>, "others"
         as the default subcategory; folders without categories stay flat)
- clone: clone repositories from a registry file into the folder directory
         (categorized registries restore each project to its recorded path)
- list:  list repositories declared in a registry file (grouped when categorized)`,
}

func init() {
}
