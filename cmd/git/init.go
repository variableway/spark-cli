package git

import (
	"fmt"
	"path/filepath"

	"spark/internal/git"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var (
	initOwner   string
	initRepo    string
	initPrivate bool
	initSkipGh  bool
)

var initCmd = &cobra.Command{
	Use:   "init",
	Short: "Initialize a git repository and create a GitHub remote",
	Long: `Initialize the current directory as a git repository:
1. Run 'git init'
2. Configure git user (name/email)
3. Add child GitHub repos as git submodules
4. Generate a .gitignore with common patterns
5. Create an initial commit
6. Create a GitHub remote repository via 'gh repo create --push'

The repo name defaults to the current directory name.
Owner defaults to the 'github-owner' config value in ~/.spark.yaml.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		repoPath := "."

		owner := initOwner
		if owner == "" {
			owner = viper.GetString("github-owner")
		}
		if owner == "" {
			return fmt.Errorf("GitHub owner is required. Set --owner flag or 'github-owner' in ~/.spark.yaml")
		}

		repoName := initRepo
		if repoName == "" {
			repoName = filepath.Base(repoPath)
			absPath, err := filepath.Abs(repoPath)
			if err == nil {
				repoName = filepath.Base(absPath)
			}
		}

		fmt.Printf("Initializing git repository: %s/%s\n", owner, repoName)
		fmt.Println()

		fmt.Println("Step 1/6: Running git init...")
		if err := git.InitRepo(repoPath); err != nil {
			return fmt.Errorf("git init failed: %w", err)
		}

		fmt.Println("Step 2/6: Configuring git user...")
		username := viper.GetString("git.username")
		email := viper.GetString("git.email")
		if username != "" && email != "" {
			if err := git.SetUserConfig(repoPath, username, email); err != nil {
				fmt.Printf("Warning: failed to set git user config: %v\n", err)
			} else {
				fmt.Printf("  user.name:  %s\n", username)
				fmt.Printf("  user.email: %s\n", email)
			}
		} else {
			fmt.Println("  No git user configured in ~/.spark.yaml. Skipping.")
		}

		fmt.Println("Step 3/6: Scanning for child GitHub repos to add as submodules...")
		if err := git.AddChildReposAsSubmodules(repoPath); err != nil {
			fmt.Printf("Warning: %v\n", err)
		}

		fmt.Println("Step 4/6: Generating .gitignore...")
		if err := git.WriteGitIgnore(repoPath); err != nil {
			fmt.Printf("Warning: failed to write .gitignore: %v\n", err)
		} else {
			fmt.Println("  .gitignore created")
		}

		fmt.Println("Step 5/6: Creating initial commit...")
		if err := git.InitialCommit(repoPath, "chore: initial commit via spark git init"); err != nil {
			fmt.Printf("Warning: initial commit failed: %v\n", err)
		}

		if !initSkipGh {
			fmt.Printf("Step 6/6: Creating GitHub remote repository (%s/%s)...\n", owner, repoName)
			if err := git.CreateGitHubRepo(repoPath, owner, repoName, initPrivate); err != nil {
				return fmt.Errorf("creating GitHub repository failed: %w", err)
			}
		} else {
			fmt.Println("Step 6/6: Skipping GitHub remote creation (--skip-gh)")
		}

		fmt.Println()
		fmt.Printf("Repository initialized: %s/%s\n", owner, repoName)
		return nil
	},
}

func init() {
	initCmd.Flags().StringVar(&initOwner, "owner", "", "GitHub owner (default: from config file)")
	initCmd.Flags().StringVarP(&initRepo, "repo", "r", "", "Repository name (default: current directory name)")
	initCmd.Flags().BoolVar(&initPrivate, "private", false, "Create a private repository")
	initCmd.Flags().BoolVar(&initSkipGh, "skip-gh", false, "Skip creating GitHub remote repository")

	GitCmd.AddCommand(initCmd)
}
