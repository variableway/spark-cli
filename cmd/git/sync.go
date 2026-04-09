package git

import (
	"fmt"
	"spark/internal/mono"

	"github.com/spf13/cobra"
)

var syncCmd = &cobra.Command{
	Use:   "sync [mono-repo-path]",
	Short: "Sync all submodules in the mono repo to the latest version",
	Long:  `Update all submodules in the mono repository to their latest versions using a single git command.`,
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		monoRepoPath := args[0]

		fmt.Printf("Syncing all submodules in: %s\n", monoRepoPath)

		if err := mono.SyncSubmodules(monoRepoPath); err != nil {
			return fmt.Errorf("failed to sync submodules: %w", err)
		}

		fmt.Println("All submodules synced successfully!")
		return nil
	},
}

func init() {
	MonoCmd.AddCommand(syncCmd)
}
