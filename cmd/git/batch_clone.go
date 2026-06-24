package git

import (
	"fmt"
	"os"
	"os/exec"
	"strings"

	"spark/internal/github"
	"spark/internal/gitlab"

	"github.com/spf13/cobra"
)

var (
	batchCloneUseSSH      bool
	batchCloneInclude     string
	batchCloneExclude     string
	batchCloneIncludeFork bool
	batchCloneOutput      string
	batchCloneToken       string
)

var batchCloneCmd = &cobra.Command{
	Use:   "batch-clone <account-name-or-url>",
	Short: "Clone all repositories from a GitHub organization or GitLab group/user",
	Long: `Clone all repositories from a GitHub organization/user or GitLab group/user.

This command will:
1. Detect whether the input is GitHub or GitLab
2. Fetch all public repositories from the specified account
3. Clone each repository to the current directory (or specified output directory)

GitHub:
  spark git batch-clone variableway
  spark git batch-clone https://github.com/variableway

GitLab (self-hosted or gitlab.com):
  spark git batch-clone https://git.cew.io/carbonnt/cyacle/domain
  spark git batch-clone https://gitlab.com/mygroup/myproject

For private GitLab instances, use --token or set GITLAB_TOKEN env var.`,
	Args: cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		input := args[0]
		outputDir := batchCloneOutput
		if outputDir == "" {
			outputDir = "."
		}

		token := batchCloneToken
		if token == "" {
			token = os.Getenv("GITLAB_TOKEN")
		}
		if token == "" {
			token = os.Getenv("GITLAB_PRIVATE_TOKEN")
		}

		if gitlab.IsGitLabURL(input) {
			return runGitLabBatchClone(input, outputDir, token)
		}

		return runGitHubBatchClone(input, outputDir)
	},
}

func runGitHubBatchClone(input, outputDir string) error {
	accountName, err := github.ParseAccountFromURL(input)
	if err != nil {
		return err
	}

	fmt.Printf("Detecting account type for: %s (GitHub)\n", accountName)

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
}

func runGitLabBatchClone(input, outputDir, token string) error {
	baseURL, groupPath, err := gitlab.ParseGitLabURL(input)
	if err != nil {
		return err
	}

	fmt.Printf("GitLab instance: %s\n", baseURL)
	fmt.Printf("Fetching projects from: %s\n\n", groupPath)

	projects, accountType, err := gitlab.GetReposForAccount(baseURL, groupPath, token)
	if err != nil {
		return err
	}

	fmt.Printf("Found %d projects for %s: %s\n\n", len(projects), accountType, groupPath)

	var projectsToClone []gitlab.Project
	for _, p := range projects {
		if !batchCloneIncludeFork && p.ForkedFrom != nil {
			continue
		}
		if batchCloneExclude != "" && matchesPattern(p.Path, batchCloneExclude) {
			continue
		}
		if batchCloneInclude != "" && !matchesPattern(p.Path, batchCloneInclude) {
			continue
		}
		projectsToClone = append(projectsToClone, p)
	}

	fmt.Printf("Cloning %d projects...\n\n", len(projectsToClone))

	successCount := 0
	skipCount := 0
	failCount := 0

	for i, project := range projectsToClone {
		fmt.Printf("[%d/%d] ", i+1, len(projectsToClone))

		repoPath := fmt.Sprintf("%s/%s", outputDir, project.Path)
		if _, err := os.Stat(repoPath); !os.IsNotExist(err) {
			fmt.Printf("Skipping %s (already exists)\n", project.Path)
			skipCount++
			continue
		}

		var cloneURL string
		if batchCloneUseSSH {
			cloneURL = project.SSHURL
		} else {
			cloneURL = project.HTTPURL
		}

		fmt.Printf("Cloning %s...\n", project.Path)

		parentDir := fmt.Sprintf("%s/%s", outputDir, dirName(project.Path))
		if err := os.MkdirAll(parentDir, 0755); err != nil {
			fmt.Printf("  Error: failed to create directory %s: %v\n", parentDir, err)
			failCount++
			continue
		}

		cloneCmd := exec.Command("git", "clone", cloneURL, repoPath)
		cloneCmd.Stdout = os.Stdout
		cloneCmd.Stderr = os.Stderr

		if err := cloneCmd.Run(); err != nil {
			fmt.Printf("  Error: failed to clone %s: %v\n", project.Path, err)
			failCount++
		} else {
			fmt.Printf("  Successfully cloned %s\n", project.Path)
			successCount++
		}
	}

	fmt.Printf("\n--- Summary ---\n")
	fmt.Printf("Cloned: %d\n", successCount)
	fmt.Printf("Skipped: %d\n", skipCount)
	fmt.Printf("Failed: %d\n", failCount)

	return nil
}

func dirName(pathWithNamespace string) string {
	parts := strings.Split(pathWithNamespace, "/")
	if len(parts) > 1 {
		return parts[len(parts)-1]
	}
	return pathWithNamespace
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
	batchCloneCmd.Flags().StringVar(&batchCloneToken, "token", "", "GitLab private token (or set GITLAB_TOKEN env var)")
}
