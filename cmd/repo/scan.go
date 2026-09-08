package repo

import (
	"fmt"
	"path/filepath"

	"spark/internal/registry"

	"github.com/spf13/cobra"
)

var scanCmd = &cobra.Command{
	Use:   "scan [folder-name]",
	Short: "Scan a folder for git repositories and save to registry_<folder>.yaml",
	Long: `Recursively scan a folder for git repositories that have an origin remote and
write them to a registry file named registry_<folder>.yaml in the current directory.

The registry records each repository's name, remote URL and relative path. Re-scanning
merges results and preserves existing descriptions.`,
	Args: cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		folder := "."
		if len(args) > 0 {
			folder = args[0]
		}

		absFolder, err := filepath.Abs(folder)
		if err != nil {
			return fmt.Errorf("resolve folder: %w", err)
		}

		projects, err := registry.Scan(absFolder)
		if err != nil {
			return err
		}

		folderName := filepath.Base(absFolder)
		registryFile := fmt.Sprintf("registry_%s.yaml", folderName)

		existing, err := registry.Read(registryFile)
		if err != nil {
			return err
		}

		final := registry.Merge(existing.Projects, projects)
		if err := registry.Write(registryFile, &registry.Registry{Projects: final}); err != nil {
			return err
		}

		fmt.Printf("Scanned %s: found %d repositories\n", absFolder, len(projects))
		for _, p := range projects {
			fmt.Printf("  %s -> %s\n", p.Path, p.Repo)
		}
		fmt.Printf("Wrote %d projects to %s\n", len(final), registryFile)
		return nil
	},
}

func init() {
	RepoCmd.AddCommand(scanCmd)
}
