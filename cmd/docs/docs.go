package docs

import (
	"github.com/spf13/cobra"
)

var DocsCmd = &cobra.Command{
	Use:   "docs",
	Short: "Documentation management commands",
	Long: `Manage project documentation structure and site configuration.

This includes:
- init: Create docs folder structure
- site: Initialize docmd site configuration`,
}

func init() {
}
