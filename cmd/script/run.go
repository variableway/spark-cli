package script

import (
	"fmt"
	"spark/internal/script"

	"github.com/fatih/color"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var runCmd = &cobra.Command{
	Use:   "run <script-name> [args...]",
	Short: "Execute a script",
	Long: `Execute a script by name.

Scripts are searched in this order:
1. Scripts defined in ~/.spark.yaml (spark.scripts)
2. Script files in the scripts/ directory

Arguments after the script name are passed to the script.`,
	Args: cobra.MinimumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		scriptName := args[0]
		scriptArgs := args[1:]

		scriptsDir := viper.GetString("spark.scripts_dir")
		if scriptsDir == "" {
			scriptsDir = "scripts"
		}

		manager := script.NewScriptManager(scriptsDir)

		// Find script
		s, err := manager.GetScript(scriptName)
		if err != nil {
			return err
		}

		// Display info
		infoColor := color.New(color.FgBlue)
		if s.Path != "" {
			infoColor.Printf("Running script '%s' from %s\n", scriptName, s.Path)
		} else {
			infoColor.Printf("Running script '%s' from config\n", scriptName)
		}

		if len(scriptArgs) > 0 {
			fmt.Printf("Arguments: %v\n", scriptArgs)
		}
		fmt.Println()

		// Run script
		if err := manager.Run(scriptName, scriptArgs); err != nil {
			return fmt.Errorf("script execution failed: %w", err)
		}

		return nil
	},
}
