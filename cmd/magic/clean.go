package magic

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/pterm/pterm"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var cleanMode string

var cleanCmd = &cobra.Command{
	Use:   "clean",
	Short: "Clean up project directories",
	Long: `Clean up node_modules and .venv directories recursively.

Examples:
  spark magic clean              # Clean both node_modules and .venv
  spark magic clean -m node      # Clean only node_modules
  spark magic clean -m python    # Clean only .venv`,
	RunE: func(cmd *cobra.Command, args []string) error {
		paths := viper.GetStringSlice("repo-path")
		if len(paths) == 0 {
			paths = []string{"."}
		}

		cleanNode := cleanMode == "" || cleanMode == "node"
		cleanPython := cleanMode == "" || cleanMode == "python"

		if !cleanNode && !cleanPython {
			return fmt.Errorf("invalid mode: %s. Supported modes: node, python", cleanMode)
		}

		var targets []string
		if cleanNode {
			targets = append(targets, "node_modules")
		}
		if cleanPython {
			targets = append(targets, ".venv")
		}

		var cleaned []string
		var errs []error

		for _, root := range paths {
			err := filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
				if err != nil {
					return nil
				}

				if d.IsDir() && d.Name() == ".git" {
					return filepath.SkipDir
				}

				if !d.IsDir() {
					return nil
				}

				for _, target := range targets {
					if d.Name() == target {
						if err := os.RemoveAll(path); err != nil {
							errs = append(errs, fmt.Errorf("failed to remove %s: %w", path, err))
						} else {
							cleaned = append(cleaned, path)
						}
						return filepath.SkipDir
					}
				}

				return nil
			})
			if err != nil {
				errs = append(errs, err)
			}
		}

		if len(cleaned) > 0 {
			pterm.Success.Printf("Cleaned %d directorie(s):\n", len(cleaned))
			for _, c := range cleaned {
				pterm.Printf("  - %s\n", c)
			}
		} else {
			pterm.Info.Println("No directories to clean.")
		}

		if len(errs) > 0 {
			pterm.Println()
			pterm.Error.Printf("Encountered %d error(s):\n", len(errs))
			for _, e := range errs {
				pterm.Printf("  - %v\n", e)
			}
			return fmt.Errorf("cleanup completed with errors")
		}

		return nil
	},
}

func init() {
	cleanCmd.Flags().StringVarP(&cleanMode, "mode", "m", "", "Cleanup mode: node, python (default: both)")
	MagicCmd.AddCommand(cleanCmd)
}
