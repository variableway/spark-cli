package resource

import (
	"github.com/spf13/cobra"
)

var ResourceCmd = &cobra.Command{
	Use:   "resource",
	Short: "System resource monitoring commands",
	Long: `Commands for monitoring system resources:

- top: Display processes, ports, and resource groups in TUI or summary mode`,
}

func init() {
}