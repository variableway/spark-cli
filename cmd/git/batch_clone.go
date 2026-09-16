package git

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"spark/internal/github"
	"spark/internal/gitlab"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
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
  spark git batch-clone https://gitlab.example.com/myorg/mygroup/mysubgroup
  spark git batch-clone https://gitlab.example.com/myorg/mygroup/mysubgroup --token <token>
  spark git batch-clone gitlab.example.com/myorg/mygroup/mysubgroup
  spark git batch-clone https://gitlab.com/mygroup/myproject

Nested groups are supported at any depth and cloned recursively (include_subgroups).
Each project is written to <output>/<namespace-relative-path> so that subgroups
are preserved and same-named projects never collide.

For private GitLab instances, provide a token via --token, the GITLAB_TOKEN
(or GITLAB_PRIVATE_TOKEN) env var, or gitlab.token in ~/.spark.yaml.
It needs the read_api scope, plus read_repository to clone private repositories.
Alternatively authenticate glab: glab auth login --hostname <your-gitlab-host>`,
	Args: cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		input := args[0]
		outputDir := batchCloneOutput
		if outputDir == "" {
			outputDir = "."
		}

		if gitlab.IsGitLabURL(input) {
			return runGitLabBatchClone(cmd, input, outputDir)
		}

		return runGitHubBatchClone(input, outputDir)
	},
}

// resolveGitLabToken resolves the credential and the place it came from.
// gitlab.host, when set, scopes the automatically discovered credentials
// (config file and env vars) to that instance; --token is always used.
func resolveGitLabToken(cmd *cobra.Command, targetHost string) (string, string) {
	if cmd.Flags().Changed("token") {
		flagToken, _ := cmd.Flags().GetString("token")
		return flagToken, gitlab.TokenSourceFlag
	}

	configHost := viper.GetString("gitlab.host")
	scoped := func(source string) bool {
		if configHost == "" || gitlab.ExtractHost(configHost) == targetHost {
			return true
		}
		fmt.Fprintf(os.Stderr, "Ignoring %s: it is scoped to %s, but the current instance is %s\n", source, configHost, targetHost)
		return false
	}

	if token := viper.GetString("gitlab.token"); token != "" && scoped(gitlab.TokenSourceConfig) {
		return token, gitlab.TokenSourceConfig
	}
	if token := os.Getenv("GITLAB_TOKEN"); token != "" && scoped(gitlab.TokenSourceEnv) {
		return token, gitlab.TokenSourceEnv
	}
	if token := os.Getenv("GITLAB_PRIVATE_TOKEN"); token != "" && scoped(gitlab.TokenSourceEnvAlt) {
		return token, gitlab.TokenSourceEnvAlt
	}
	return "", ""
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

func runGitLabBatchClone(cmd *cobra.Command, input, outputDir string) error {
	baseURL, groupPath, err := gitlab.ParseGitLabURL(input)
	if err != nil {
		return err
	}

	token, tokenSource := resolveGitLabToken(cmd, gitlab.ExtractHost(baseURL))

	fmt.Printf("GitLab instance: %s\n", baseURL)
	fmt.Printf("Fetching projects from: %s\n", groupPath)
	if token != "" {
		fmt.Printf("Using token from: %s\n", tokenSource)
	}
	fmt.Println()

	projects, accountType, err := gitlab.GetReposForAccount(baseURL, groupPath, token, tokenSource)
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

		relPath := gitlab.ProjectRelativePath(project, groupPath)
		repoPath := filepath.Join(outputDir, relPath)
		if _, err := os.Stat(repoPath); !os.IsNotExist(err) {
			fmt.Printf("Skipping %s (already exists)\n", relPath)
			skipCount++
			continue
		}

		var cloneURL string
		if batchCloneUseSSH {
			cloneURL = project.SSHURL
		} else {
			cloneURL = project.HTTPURL
		}

		fmt.Printf("Cloning %s...\n", relPath)

		if err := os.MkdirAll(filepath.Dir(repoPath), 0755); err != nil {
			fmt.Printf("  Error: failed to create directory %s: %v\n", filepath.Dir(repoPath), err)
			failCount++
			continue
		}

		cloneCmd := exec.Command("git", "clone", cloneURL, repoPath)
		cloneCmd.Stdout = os.Stdout
		cloneCmd.Stderr = os.Stderr

		if err := cloneCmd.Run(); err != nil {
			fmt.Printf("  Error: failed to clone %s: %v\n", relPath, err)
			failCount++
		} else {
			fmt.Printf("  Successfully cloned %s\n", relPath)
			successCount++
		}
	}

	fmt.Printf("\n--- Summary ---\n")
	fmt.Printf("Cloned: %d\n", successCount)
	fmt.Printf("Skipped: %d\n", skipCount)
	fmt.Printf("Failed: %d\n", failCount)

	return nil
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
	batchCloneCmd.Flags().StringVar(&batchCloneToken, "token", "", "GitLab private token (or set GITLAB_TOKEN env var, or gitlab.token in ~/.spark.yaml)")

	viper.BindPFlag("gitlab.token", batchCloneCmd.Flags().Lookup("token"))
}
