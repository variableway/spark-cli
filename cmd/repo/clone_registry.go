package repo

import (
	"fmt"
	"os"
	"path/filepath"

	"spark/internal/registry"

	"github.com/spf13/cobra"
)

var (
	cloneRegistryOut    string
	cloneRegistryDryRun bool
	cloneRegistryDepth  int
)

var cloneRegistryCmd = &cobra.Command{
	Use:   "clone-registry <registry-file>",
	Short: "Clone only the registry entries missing on disk",
	Long: `Clone the repositories declared in a registry file whose target directory does
not exist yet — the restore counterpart of repo scan, which keeps entries that
are not checked out locally.

The registry file is a positional argument. The destination folder is derived
from the registry file's location and name (path/to/registry_<folder>.yaml ->
path/to/<folder>/), so the registry restores the tree it sits next to no matter
the current directory; override with --out. Entries already on disk are skipped
and counted, never re-cloned. --dry-run prints the plan without cloning, and
--depth N clones shallowly (git clone --depth=N; 0 = full history).`,
	Example: `  spark repo clone-registry registry_references.yaml
  spark repo clone-registry /path/to/registry_references.yaml --dry-run
  spark repo clone-registry registry_references.yaml --depth 1
  spark repo clone-registry registry_references.yaml --out ~/innate/base/innate-skills/references`,
	Args: cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		regFile := args[0]

		reg, err := registry.Read(regFile)
		if err != nil {
			return err
		}

		projects := reg.AllProjects()
		if len(projects) == 0 {
			fmt.Println("No repositories in registry.")
			return nil
		}

		root := cloneRegistryOut
		if root == "" {
			root = filepath.Join(filepath.Dir(regFile), folderFromRegistryFile(regFile))
		}

		// Split present/missing up front so the plan is visible before any
		// network traffic; --dry-run stops right there.
		sortByDepth(projects)
		var missing, present []registry.Project
		for _, p := range projects {
			if _, err := os.Stat(registry.TargetPath(root, p)); err == nil {
				present = append(present, p)
			} else {
				missing = append(missing, p)
			}
		}
		fmt.Printf("Registry %s -> %s: %d entries, %d on disk, %d missing\n",
			regFile, root, len(projects), len(present), len(missing))
		for _, p := range present {
			fmt.Printf("SKIP %s (already exists)\n", registry.TargetPath(root, p))
		}

		if cloneRegistryDryRun {
			for _, p := range missing {
				fmt.Printf("WOULD CLONE %s -> %s\n", p.Repo, registry.TargetPath(root, p))
			}
			fmt.Printf("\nDry run: %d would be cloned, %d skipped\n", len(missing), len(present))
			return nil
		}

		cloned, _, failed := cloneProjects(missing, root, cloneRegistryDepth)

		fmt.Printf("\nDone: cloned %d, skipped %d (existing), failed %d\n", cloned, len(present), failed)
		if failed > 0 {
			return fmt.Errorf("%d repositories failed to clone", failed)
		}
		return nil
	},
}

func init() {
	cloneRegistryCmd.Flags().StringVar(&cloneRegistryOut, "out", "", "Destination folder (default: next to the registry file, derived from its name)")
	cloneRegistryCmd.Flags().BoolVar(&cloneRegistryDryRun, "dry-run", false, "Print what would be cloned without cloning")
	cloneRegistryCmd.Flags().IntVar(&cloneRegistryDepth, "depth", 0, "Shallow clone depth (0 = full history)")
	RepoCmd.AddCommand(cloneRegistryCmd)
}
