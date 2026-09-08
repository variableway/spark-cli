package repo

import (
	"fmt"

	"spark/internal/registry"

	"github.com/spf13/cobra"
)

var listFile string

var listCmd = &cobra.Command{
	Use:   "list",
	Short: "List repositories declared in a registry file",
	Long:  `List repositories declared in a registry file (name, remote URL and path).`,
	Example: `  spark repo list -f registry_innate-apps.yaml`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if listFile == "" {
			return fmt.Errorf("registry file is required: use -f registry_<folder>.yaml")
		}

		reg, err := registry.Read(listFile)
		if err != nil {
			return err
		}

		if len(reg.Projects) == 0 {
			fmt.Println("No repositories in registry.")
			return nil
		}

		for _, p := range reg.Projects {
			fmt.Printf("%s\t%s\t%s\n", p.Name, p.Repo, p.Path)
		}
		return nil
	},
}

func init() {
	listCmd.Flags().StringVarP(&listFile, "file", "f", "", "Registry file (registry_<folder>.yaml)")
	RepoCmd.AddCommand(listCmd)
}
