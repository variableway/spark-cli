package git

import (
	"fmt"
	"monolize/internal/github"
	"os"
	"os/exec"
	"strings"

	"github.com/spf13/cobra"
)

var (
	cloneOrgUseSSH   bool
	cloneOrgInclude  string
	cloneOrgExclude  string
	cloneOrgIncludeFork bool
	cloneOrgOutput   string
)

var cloneOrgCmd = &cobra.Command{
	Use:   "clone-org <org-name-or-url>",
	Short: "Clone all repositories from a GitHub organization",
	Long: `Clone all repositories from a GitHub organization.

This command will:
1. Fetch all public repositories from the specified organization
2. Clone each repository to the current directory (or specified output directory)

You can provide either the organization name (e.g., "variableway") 
or the full GitHub URL (e.g., "https://github.com/variableway").`,
	Args: cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		input := args[0]
		
		orgName, err := github.ParseOrgFromURL(input)
		if err != nil {
			return err
		}

		outputDir := cloneOrgOutput
		if outputDir == "" {
			outputDir = "."
		}

		fmt.Printf("Fetching repositories for organization: %s\n", orgName)
		
		repos, err := github.GetOrgRepos(orgName)
		if err != nil {
			return err
		}

		fmt.Printf("Found %d repositories\n\n", len(repos))

		var reposToClone []github.Repository
		for _, repo := range repos {
			if !cloneOrgIncludeFork && repo.Fork {
				continue
			}

			if cloneOrgExclude != "" && matchesPattern(repo.Name, cloneOrgExclude) {
				continue
			}

			if cloneOrgInclude != "" && !matchesPattern(repo.Name, cloneOrgInclude) {
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
			if cloneOrgUseSSH {
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
	GitCmd.AddCommand(cloneOrgCmd)
	
	cloneOrgCmd.Flags().BoolVar(&cloneOrgUseSSH, "ssh", false, "Use SSH URLs instead of HTTPS")
	cloneOrgCmd.Flags().StringVar(&cloneOrgInclude, "include", "", "Include only repos matching pattern (comma-separated)")
	cloneOrgCmd.Flags().StringVar(&cloneOrgExclude, "exclude", "", "Exclude repos matching pattern (comma-separated)")
	cloneOrgCmd.Flags().BoolVar(&cloneOrgIncludeFork, "include-forks", false, "Include forked repositories")
	cloneOrgCmd.Flags().StringVarP(&cloneOrgOutput, "output", "o", ".", "Output directory for cloned repositories")
}
