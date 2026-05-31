package magic

import (
	"github.com/spf13/cobra"
)

var MagicCmd = &cobra.Command{
	Use:   "magic",
	Short: "System utility commands",
	Long: `System utility commands that make your life easier.

This includes:
- flush-dns: Flush DNS cache on macOS, Windows, or Linux
- copy-config: Deploy bundled Neovim and Ghostty config templates to a PC`,
}

func init() {
}
