package git

import (
	"fmt"
	"spark/internal/git"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var gitUsername string
var gitEmail string

var configCmd = &cobra.Command{
	Use:   "config",
	Short: "Configure git user for the current repository",
	Long: `Configure git user.name and user.email for the current repository.
This command will:
1. Read default username and email from config file (~/.spark.yaml)
2. Apply them to the current repository (local git config)
3. Optionally override with --username and --email flags`,
	RunE: func(cmd *cobra.Command, args []string) error {
		repoPath := "."
		if len(args) > 0 {
			repoPath = args[0]
		}

		if gitUsername == "" {
			gitUsername = viper.GetString("git.username")
		}
		if gitEmail == "" {
			gitEmail = viper.GetString("git.email")
		}

		if gitUsername == "" || gitEmail == "" {
			currentUser, currentEmail, err := git.GetUserConfig(repoPath)
			if err != nil {
				return fmt.Errorf("failed to get current git config: %w", err)
			}
			fmt.Println("Current git configuration:")
			fmt.Printf("  user.name:  %s\n", currentUser)
			fmt.Printf("  user.email: %s\n", currentEmail)
			fmt.Println()
			fmt.Println("No username or email provided.")
			fmt.Println("Please either:")
			fmt.Println("  1. Set git.username and git.email in ~/.spark.yaml")
			fmt.Println("  2. Use --username and --email flags")
			return nil
		}

		currentUser, currentEmail, err := git.GetUserConfig(repoPath)
		if err != nil {
			return fmt.Errorf("failed to get current git config: %w", err)
		}

		fmt.Printf("Setting git config for: %s\n", repoPath)
		fmt.Printf("  user.name:  %s -> %s\n", currentUser, gitUsername)
		fmt.Printf("  user.email: %s -> %s\n", currentEmail, gitEmail)

		if err := git.SetUserConfig(repoPath, gitUsername, gitEmail); err != nil {
			return fmt.Errorf("failed to set git config: %w", err)
		}

		fmt.Println("\nGit configuration updated successfully!")
		return nil
	},
}

func init() {
	GitCmd.AddCommand(configCmd)
	configCmd.Flags().StringVar(&gitUsername, "username", "", "Git username (default: from config file)")
	configCmd.Flags().StringVar(&gitEmail, "email", "", "Git email (default: from config file)")
}
