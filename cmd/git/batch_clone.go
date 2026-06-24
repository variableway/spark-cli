package git

import (
	"fmt"
	"spark/internal/github"
	"os"
	"os/exec"
	"strings"

	"github.com/spf13/cobra"
)

var (
	batchCloneUseSSH      bool
	batchCloneInclude     string
	batchCloneExclude     string
	batchCloneIncludeFork bool
	batchCloneOutput      string
)

var batchCloneCmd = &cobra.Command{
	Use:   "batch-clone <account-name-or-url>",
	Short: "Clone all repositories from a GitHub organization or user",
	Long: `Clone all repositories from a GitHub organization or user account.

This command will:
1. Detect whether the account is an organization or a user
2. Fetch all public repositories from the specified account
3. Clone each repository to the current directory (or specified output directory)

You can provide either the account name (e.g., "jackwener" or "variableway") 
or the full GitHub URL (e.g., "https://github.com/jackwener").`,
	Args: cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		input := args[0]

		accountName, err := github.ParseAccountFromURL(input)
		if err != nil {
			return err
		}

		outputDir := batchCloneOutput
		if outputDir == "" {
			outputDir = "."
		}

		fmt.Printf("Detecting account type for: %s\n", accountName)

		repos, accountType, err := github.GetReposForAccount(accountName)
		if err != nil {
			return err
		}

		accountTypeLabel := "organization"
		if accountType == github.AccountTypeUser {
			accountTypeLabel = "user"
		}
		fmt.Printf("Found %d repositories for %s: %s\n\n", len(repos), accountTypeLabel, accountName)

		var reposToClone []github.Repository
		for _, repo := range repos {
			if !batchCloneIncludeFork && repo.Fork {
				continue
			}

			if batchCloneExclude != "" && matchesPattern(repo.Name, batchCloneExclude) {
				continue
			}

			if batchCloneInclude != "" && !matchesPattern(repo.Name, batchCloneInclude) {
				continue
			}

			reposToClone = append(reposToClone, repo)
		}

		fmt.Printf("Cloning %d repositories...\n\n", len(reposToClone))

		successCount := 0
		skipCount := 0
		failCount := 0

		for i, repo := range reposToClone {
			fmt.Printf("[%d/%d] ", i+1, len(reposToClone))

			repoPath := fmt.Sprintf("%s/%s", outputDir, repo.Name)
			if _, err := os.Stat(repoPath); !os.IsNotExist(err) {
				fmt.Printf("Skipping %s (already exists)\n", repo.Name)
				skipCount++
				continue
			}

			var cloneURL string
			if batchCloneUseSSH {
				cloneURL = repo.SSHURL
			} else {
				cloneURL = repo.CloneURL
			}

			fmt.Printf("Cloning %s...\n", repo.Name)

			cloneCmd := exec.Command("git", "clone", cloneURL, repoPath)
			cloneCmd.Stdout = os.Stdout
			cloneCmd.Stderr = os.Stderr

			if err := cloneCmd.Run(); err != nil {
				fmt.Printf("  Error: failed to clone %s: %v\n", repo.Name, err)
				failCount++
			} else {
				fmt.Printf("  Successfully cloned %s\n", repo.Name)
				successCount++
			}
		}

		fmt.Printf("\n--- Summary ---\n")
		fmt.Printf("Cloned: %d\n", successCount)
		fmt.Printf("Skipped: %d\n", skipCount)
		fmt.Printf("Failed: %d\n", failCount)

		return nil
	},
}

func matchesPattern(name, pattern string) bool {
	if pattern == "" {
		return true
	}

	patterns := strings.Split(pattern, ",")
	for _, p := range patterns {
		p = strings.TrimSpace(p)
		if p != "" && strings.Contains(name, p) {
			return true
		}
	}
	return false
}

func init() {
	GitCmd.AddCommand(batchCloneCmd)

	batchCloneCmd.Flags().BoolVar(&batchCloneUseSSH, "ssh", false, "Use SSH URLs instead of HTTPS")
	batchCloneCmd.Flags().StringVar(&batchCloneInclude, "include", "", "Include only repos matching pattern (comma-separated)")
	batchCloneCmd.Flags().StringVar(&batchCloneExclude, "exclude", "", "Exclude repos matching pattern (comma-separated)")
	batchCloneCmd.Flags().BoolVar(&batchCloneIncludeFork, "include-forks", false, "Include forked repositories")
	batchCloneCmd.Flags().StringVarP(&batchCloneOutput, "output", "o", ".", "Output directory for cloned repositories")
}
