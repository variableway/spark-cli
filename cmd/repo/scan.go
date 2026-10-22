package repo

import (
	"fmt"
	"path/filepath"

	"spark/internal/registry"

	"github.com/spf13/cobra"
)

var (
	scanJSON    bool
	scanFlatten bool
)

var scanCmd = &cobra.Command{
	Use:   "scan [folder-name]",
	Short: "Scan a folder for git repositories and save to registry_<folder>.yaml",
	Long: `Recursively scan a folder for git repositories that have an origin remote and
write them to a registry file named registry_<folder>.yaml in the current directory.

The folder is expected to hold a two-level layout: the first level is the category
and the second level holds the actual repositories. With --flatten, repositories
nested deeper than two levels are moved up into the two-level layout (no files are
overwritten; conflicts are reported and left in place) before scanning. With --json,
an additional registry_<folder>.json file with the same content is written.

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

		if scanFlatten {
			result, err := registry.Flatten(absFolder)
			if err != nil {
				return err
			}
			for _, m := range result.Moves {
				fmt.Printf("Flattened %s -> %s\n", m.From, m.To)
			}
			for _, c := range result.Conflicts {
				fmt.Printf("Skipped %s -> %s: %s\n", c.From, c.To, c.Reason)
			}
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

		if scanJSON {
			jsonFile := fmt.Sprintf("registry_%s.json", folderName)
			if err := registry.WriteJSON(jsonFile, &registry.Registry{Projects: final}); err != nil {
				return err
			}
			fmt.Printf("Wrote %d projects to %s\n", len(final), jsonFile)
		}
		return nil
	},
}

func init() {
	scanCmd.Flags().BoolVar(&scanJSON, "json", false, "additionally write registry_<folder>.json")
	scanCmd.Flags().BoolVar(&scanFlatten, "flatten", false, "move repositories deeper than two levels up into the category/repo layout before scanning")
	RepoCmd.AddCommand(scanCmd)
}
