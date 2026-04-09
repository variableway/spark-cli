package git

import (
	"github.com/spf13/cobra"
)

var MonoCmd = &cobra.Command{
	Use:   "mono",
	Short: "Mono repo management commands",
	Long: `Commands for managing mono repositories with git submodules.

This includes:
- add: Add existing git repos in current folder as submodules
- sync: Sync all submodules to latest versions`,
}

func init() {
	GitCmd.AddCommand(MonoCmd)
}
