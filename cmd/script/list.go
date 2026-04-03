package script

import (
	"fmt"
	"monolize/internal/script"

	"github.com/fatih/color"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var listCmd = &cobra.Command{
	Use:   "list",
	Short: "List all available scripts",
	Long:  `List all scripts defined in configuration and in the scripts/ directory.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		scriptsDir := viper.GetString("spark.scripts_dir")
		if scriptsDir == "" {
			scriptsDir = "scripts"
		}

		manager := script.NewScriptManager(scriptsDir)

		// Get scripts from config
		configScripts, err := manager.LoadScriptsFromConfig()
		if err != nil {
			// Non-fatal error
			configScripts = []script.Script{}
		}

		// Get scripts from directory
		dirScripts, err := manager.LoadScriptsFromDir()
		if err != nil {
			// Non-fatal error
			dirScripts = []script.Script{}
		}

		if len(configScripts) == 0 && len(dirScripts) == 0 {
			fmt.Println("No scripts found.")
			fmt.Println()
			fmt.Println("To add scripts:")
			fmt.Println("  1. Add to ~/.spark.yaml:")
			fmt.Println("     spark:")
			fmt.Println("       scripts:")
			fmt.Println("         - name: hello")
			fmt.Println("           content: |")
			fmt.Println("             #!/bin/bash")
			fmt.Println("             echo 'Hello World'")
			fmt.Println()
			fmt.Println("  2. Or create script files in ./scripts/ directory")
			return nil
		}

		headerColor := color.New(color.FgGreen, color.Bold)
		headerColor.Println("Available Scripts")
		fmt.Println()

		// Config scripts
		if len(configScripts) > 0 {
			fmt.Println("From configuration (~/.spark.yaml):")
			fmt.Println("┌─────────────────┬──────────┬─────────────┐")
			fmt.Printf("│ %-15s │ %-8s │ %-11s │\n", "Name", "Source", "Type")
			fmt.Println("├─────────────────┼──────────┼─────────────┤")
			for _, s := range configScripts {
				scriptType := "inline"
				if s.Path != "" {
					scriptType = script.GetScriptType(s.Path)
				}
				fmt.Printf("│ %-15s │ %-8s │ %-11s │\n", s.Name, "config", scriptType)
			}
			fmt.Println("└─────────────────┴──────────┴─────────────┘")
			fmt.Println()
		}

		// Directory scripts
		if len(dirScripts) > 0 {
			fmt.Printf("From scripts directory (./%s):\n", scriptsDir)
			fmt.Println("┌─────────────────┬──────────┬─────────────┬──────────────────────────────┐")
			fmt.Printf("│ %-15s │ %-8s │ %-11s │ %-28s │\n", "Name", "Source", "Type", "Path")
			fmt.Println("├─────────────────┼──────────┼─────────────┼──────────────────────────────┤")
			for _, s := range dirScripts {
				path := s.Path
				if len(path) > 28 {
					path = "..." + path[len(path)-25:]
				}
				fmt.Printf("│ %-15s │ %-8s │ %-11s │ %-28s │\n", s.Name, "file", script.GetScriptType(s.Path), path)
			}
			fmt.Println("└─────────────────┴──────────┴─────────────┴──────────────────────────────┘")
			fmt.Println()
		}

		fmt.Println("Usage:")
		fmt.Println("  spark script run <script-name> [args...]")
		fmt.Println()

		return nil
	},
}
