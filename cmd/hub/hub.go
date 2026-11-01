package hub

import (
	"github.com/spf13/cobra"
)

var HubCmd = &cobra.Command{
	Use:   "hub",
	Short: "Project hub: register local projects as innate-daily collections",
	Long: `Hub commands scan local git repositories and turn them into
innate-daily collections entries (src/data/collections.json).

Examples:
  spark hub scan ~/workspace                # scan directory, print JSON
  spark hub scan . -o collections.json      # write to a file
  spark hub scan . --skip-api --category 随意日常  # offline, custom category`,
}

func init() {
	HubCmd.AddCommand(scanCmd)
}
