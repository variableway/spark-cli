package script

import (
	"github.com/spf13/cobra"
)

var ScriptCmd = &cobra.Command{
	Use:   "script",
	Short: "Manage and execute custom scripts",
	Long: `Script management commands for running custom scripts.

Scripts can be defined in two ways:
1. Configuration in ~/.spark.yaml under spark.scripts
2. Script files in the scripts/ directory

Examples:
  spark script list              # List all available scripts
  spark script run hello         # Run the 'hello' script
  spark script run deploy prod   # Run 'deploy' script with argument 'prod'`,
}

func init() {
	ScriptCmd.AddCommand(runCmd)
	ScriptCmd.AddCommand(listCmd)
}
