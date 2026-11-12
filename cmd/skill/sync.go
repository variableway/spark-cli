package skill

import (
	"fmt"
	"spark/internal/skill"

	"github.com/spf13/cobra"
)

var clearTarget bool

var syncCmd = &cobra.Command{
	Use:   "sync <target-dir>",
	Short: "Copy all discovered skills to a target directory",
	Long: `Discover every skill in well-known locations and copy them into
the target directory. Use --clear to empty the target first.`,
	Args: cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		target := args[0]

		skills, err := skill.Discover(".")
		if err != nil {
			return err
		}
		if len(skills) == 0 {
			fmt.Println("No skills found to sync.")
			return nil
		}

		if clearTarget {
			fmt.Printf("Clearing %s ...\n", target)
		}

		copied, err := skill.Sync(skills, target, clearTarget)
		if err != nil {
			return err
		}

		fmt.Printf("Synced %d skill(s) to %s:\n", len(copied), target)
		for _, p := range copied {
			fmt.Printf("  %s\n", p)
		}
		return nil
	},
}

func init() {
	syncCmd.Flags().BoolVar(&clearTarget, "clear", false, "Clear the target directory before copying")
}
