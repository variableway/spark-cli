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

The folder is expected to hold the categorized layout:

    <category>/<subcategory>/<project>      e.g. skills/agent/taste-skill

The registry is written in the categorized format (version: 2): categories are the
folder's immediate subdirectories (so empty categories still appear), every category
always contains an "others" subcategory, and a project directly under a category
(<category>/<project>, i.e. without a subcategory) is recorded under "others".
Folders without category directories keep the legacy flat "projects" format.

With --json, an additional registry_<folder>.json file with the same content is
written. With --flatten, repositories nested deeper than two levels are moved up
into the LEGACY two-level <category>/<repo> layout first (no files are overwritten;
conflicts are reported and left in place) — do NOT pass --flatten on a categorized
<category>/<subcategory>/<project> tree, it would move projects out of their
subcategory.

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

		final := registry.Merge(existing.AllProjects(), projects)

		groups, skipped, err := registry.Categorize(absFolder, final)
		if err != nil {
			return err
		}
		// Categorized output only once at least one project actually has a
		// category (or the categorized tree holds no projects at all). A folder
		// whose projects all sit in the root keeps the legacy flat format so
		// nothing silently disappears from an existing registry.
		classified := len(final) - len(skipped)
		useCategories := len(groups) > 0 && (len(final) == 0 || classified > 0)
		reg := &registry.Registry{Projects: final}
		if useCategories {
			reg = &registry.Registry{Categories: groups}
		}
		if err := registry.Write(registryFile, reg); err != nil {
			return err
		}

		fmt.Printf("Scanned %s: found %d repositories\n", absFolder, len(projects))
		if reg.IsCategorized() {
			for _, c := range reg.Categories {
				for _, s := range c.Subcategories {
					if len(s.Projects) == 0 {
						fmt.Printf("%s / %s (0)\n", c.Name, s.Name)
						continue
					}
					fmt.Printf("%s / %s\n", c.Name, s.Name)
					for _, p := range s.Projects {
						fmt.Printf("  %s -> %s\n", p.Path, p.Repo)
					}
				}
			}
			for _, p := range skipped {
				fmt.Printf("WARNING: %s sits directly in the folder root and has no category — move it into <category>/<subcategory>/ (not written to the registry)\n", p.Path)
			}
		} else {
			if len(groups) > 0 && len(final) > 0 {
				fmt.Println("NOTE: no project has a category — wrote the legacy flat registry; move projects into <category>/<subcategory>/ to get the categorized format")
			}
			for _, p := range projects {
				fmt.Printf("  %s -> %s\n", p.Path, p.Repo)
			}
		}
		fmt.Printf("Wrote %d projects to %s\n", len(reg.AllProjects()), registryFile)

		if scanJSON {
			jsonFile := fmt.Sprintf("registry_%s.json", folderName)
			if err := registry.WriteJSON(jsonFile, reg); err != nil {
				return err
			}
			fmt.Printf("Wrote %d projects to %s\n", len(reg.AllProjects()), jsonFile)
		}
		return nil
	},
}

func init() {
	scanCmd.Flags().BoolVar(&scanJSON, "json", false, "additionally write registry_<folder>.json")
	scanCmd.Flags().BoolVar(&scanFlatten, "flatten", false, "move repositories deeper than two levels up into the category/repo layout before scanning")
	RepoCmd.AddCommand(scanCmd)
}
