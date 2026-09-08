package repo

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"spark/internal/registry"

	"github.com/spf13/cobra"
)

var (
	cloneRepoName string
	cloneFile     string
)

var cloneCmd = &cobra.Command{
	Use:   "clone",
	Short: "Clone repositories from a registry file into the folder directory",
	Long: `Clone repositories declared in a registry file into the folder directory.

The target folder name is derived from the registry file name
(registry_<folder>.yaml -> <folder>). Use -r to clone a single repository by name;
otherwise all repositories in the registry are cloned.`,
	Example: `  spark repo clone -f registry_innate-apps.yaml
  spark repo clone -r spark-cli -f registry_innate-apps.yaml`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if cloneFile == "" {
			return fmt.Errorf("registry file is required: use -f registry_<folder>.yaml")
		}

		reg, err := registry.Read(cloneFile)
		if err != nil {
			return err
		}

		projects := reg.Projects
		if cloneRepoName != "" {
			p, err := registry.FindByName(reg, cloneRepoName)
			if err != nil {
				return err
			}
			projects = []registry.Project{*p}
		}

		if len(projects) == 0 {
			fmt.Println("No repositories in registry.")
			return nil
		}

		root := folderFromRegistryFile(cloneFile)
		cloned, skipped, failed := 0, 0, 0
		for _, p := range projects {
			target := registry.TargetPath(root, p)
			if isGitRepo(target) {
				fmt.Printf("SKIP %s (already exists)\n", target)
				skipped++
				continue
			}
			if _, err := os.Stat(target); err == nil {
				fmt.Printf("SKIP %s (directory already exists)\n", target)
				skipped++
				continue
			}

			fmt.Printf("CLONE %s -> %s\n", p.Repo, target)
			if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
				fmt.Printf("  Error: create directory: %v\n", err)
				failed++
				continue
			}
			c := exec.Command("git", "clone", p.Repo, target)
			c.Stdout = os.Stdout
			c.Stderr = os.Stderr
			if err := c.Run(); err != nil {
				fmt.Printf("  Error: clone failed: %v\n", err)
				failed++
				continue
			}
			cloned++
		}

		fmt.Printf("\nDone: cloned %d, skipped %d, failed %d\n", cloned, skipped, failed)
		if failed > 0 {
			return fmt.Errorf("%d repositories failed to clone", failed)
		}
		return nil
	},
}

func folderFromRegistryFile(path string) string {
	base := filepath.Base(path)
	name := strings.TrimPrefix(base, "registry_")
	name = strings.TrimSuffix(name, filepath.Ext(name))
	return name
}

func isGitRepo(path string) bool {
	_, err := os.Stat(filepath.Join(path, ".git"))
	return err == nil
}

func init() {
	cloneCmd.Flags().StringVarP(&cloneRepoName, "repo", "r", "", "Repository name to clone (omit to clone all)")
	cloneCmd.Flags().StringVarP(&cloneFile, "file", "f", "", "Registry file (registry_<folder>.yaml)")
	RepoCmd.AddCommand(cloneCmd)
}
