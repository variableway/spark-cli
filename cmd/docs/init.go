package docs

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/pterm/pterm"
	"github.com/spf13/cobra"
)

var docsDirs = []string{
	"analysis",
	"features",
	"quick-start",
	"spec",
	"tips",
	"usage",
}

var docsFiles = []string{
	"Agents.md",
	"index.md",
	"README.md",
}

var docsInitCmd = &cobra.Command{
	Use:   "init",
	Short: "Create docs folder structure",
	Long: `Create the standard docs folder structure:

  Agents.md, analysis/, features/, index.md, quick-start/,
  README.md, spec/, tips/, usage/

Skips files and directories that already exist.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		root, err := cmd.Flags().GetString("root")
		if err != nil {
			return err
		}

		docsPath := filepath.Join(root, "docs")
		return initDocs(docsPath)
	},
}

func initDocs(docsPath string) error {
	pterm.Info.Printf("Initializing docs structure in %s\n", docsPath)

	if err := os.MkdirAll(docsPath, 0755); err != nil {
		return fmt.Errorf("failed to create docs directory: %w", err)
	}

	for _, dir := range docsDirs {
		p := filepath.Join(docsPath, dir)
		if _, err := os.Stat(p); os.IsNotExist(err) {
			if err := os.MkdirAll(p, 0755); err != nil {
				return fmt.Errorf("failed to create %s: %w", dir, err)
			}
			pterm.Success.Printf("Created directory: %s/\n", dir)
		} else {
			pterm.Info.Printf("Already exists: %s/\n", dir)
		}
	}

	for _, file := range docsFiles {
		p := filepath.Join(docsPath, file)
		if _, err := os.Stat(p); os.IsNotExist(err) {
			if err := os.WriteFile(p, []byte(""), 0644); err != nil {
				return fmt.Errorf("failed to create %s: %w", file, err)
			}
			pterm.Success.Printf("Created file: %s\n", file)
		} else {
			pterm.Info.Printf("Already exists: %s\n", file)
		}
	}

	pterm.Success.Println("Docs structure initialized.")
	return nil
}

func init() {
	docsInitCmd.Flags().String("root", ".", "Project root directory")
	DocsCmd.AddCommand(docsInitCmd)
}
