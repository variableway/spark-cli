package git

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"monolize/internal/github"

	"github.com/spf13/cobra"
)

var (
	updateOrgStatusOutput string
	updateOrgStatusDryRun bool
)

var updateOrgStatusCmd = &cobra.Command{
	Use:   "update-org-status <org-name-or-url>",
	Short: "Update organization repositories status to .github/README.md",
	Long: `Fetch all repositories from a GitHub organization, sort by stars,
and update the .github/README.md file with a project list table.

This command will:
1. Fetch all public repositories from the specified organization
2. Sort repositories by stargazers count (descending)
3. Update or create .github/README.md with a "Project List" section
4. Commit and push changes to the repository`,
	Args: cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		input := args[0]

		orgName, err := github.ParseOrgFromURL(input)
		if err != nil {
			return err
		}

		fmt.Printf("Fetching repositories for organization: %s\n", orgName)

		repos, err := github.GetOrgRepos(orgName)
		if err != nil {
			return err
		}

		fmt.Printf("Found %d repositories\n", len(repos))

		// Sort by stargazers count (descending)
		sort.Slice(repos, func(i, j int) bool {
			return repos[i].Stargazers > repos[j].Stargazers
		})

		// Generate README content
		readmeContent := generateREADME(orgName, repos)

		// Determine output path
		outputPath := updateOrgStatusOutput
		if outputPath == "" {
			outputPath = ".github/README.md"
		}

		// Ensure directory exists
		dir := filepath.Dir(outputPath)
		if err := os.MkdirAll(dir, 0755); err != nil {
			return fmt.Errorf("failed to create directory %s: %w", dir, err)
		}

		if updateOrgStatusDryRun {
			fmt.Printf("\n--- Dry Run: Would write to %s ---\n", outputPath)
			fmt.Println(readmeContent)
			return nil
		}

		// Write README file
		if err := os.WriteFile(outputPath, []byte(readmeContent), 0644); err != nil {
			return fmt.Errorf("failed to write README: %w", err)
		}

		fmt.Printf("Updated: %s\n", outputPath)

		// Git add, commit, push
		if err := gitCommitAndPush(outputPath, orgName); err != nil {
			fmt.Printf("Warning: git operations failed: %v\n", err)
			fmt.Println("You may need to manually commit and push the changes.")
		}

		return nil
	},
}

func generateREADME(orgName string, repos []github.Repository) string {
	var sb strings.Builder

	sb.WriteString(fmt.Sprintf("# %s Projects\n\n", strings.Title(orgName)))
	sb.WriteString(fmt.Sprintf("This page lists all public repositories in the **%s** organization, sorted by stars.\n\n", orgName))
	sb.WriteString(fmt.Sprintf("*Last updated: %s*\n\n", time.Now().Format("2006-01-02 15:04:05")))

	sb.WriteString("## Project List\n\n")

	// Table header
	sb.WriteString("| Name | Description | Stars | Language |\n")
	sb.WriteString("|------|-------------|-------|----------|\n")

	// Table rows
	for _, repo := range repos {
		if repo.Fork {
			continue // Skip forked repositories
		}

		desc := repo.Description
		if desc == "" {
			desc = "-"
		}
		// Escape pipe characters in description
		desc = strings.ReplaceAll(desc, "|", "\\|")

		lang := repo.Language
		if lang == "" {
			lang = "-"
		}

		sb.WriteString(fmt.Sprintf("| [%s](%s) | %s | ⭐ %d | %s |\n",
			repo.Name,
			repo.HTMLURL,
			desc,
			repo.Stargazers,
			lang,
		))
	}

	sb.WriteString("\n## Statistics\n\n")
	sb.WriteString(fmt.Sprintf("- **Total Repositories**: %d\n", len(repos)))

	// Count non-fork repos
	nonForkCount := 0
	totalStars := 0
	for _, repo := range repos {
		if !repo.Fork {
			nonForkCount++
			totalStars += repo.Stargazers
		}
	}

	sb.WriteString(fmt.Sprintf("- **Non-fork Repositories**: %d\n", nonForkCount))
	sb.WriteString(fmt.Sprintf("- **Total Stars**: %d\n", totalStars))

	if nonForkCount > 0 {
		avgStars := float64(totalStars) / float64(nonForkCount)
		sb.WriteString(fmt.Sprintf("- **Average Stars**: %.1f\n", avgStars))
	}

	return sb.String()
}

func gitCommitAndPush(filePath, orgName string) error {
	// Check if we're in a git repository
	if _, err := exec.LookPath("git"); err != nil {
		return fmt.Errorf("git not found in PATH")
	}

	// Check if file is tracked by git
	cmd := exec.Command("git", "rev-parse", "--git-dir")
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("not in a git repository")
	}

	// Git add
	fmt.Printf("Running: git add %s\n", filePath)
	addCmd := exec.Command("git", "add", filePath)
	addCmd.Stdout = os.Stdout
	addCmd.Stderr = os.Stderr
	if err := addCmd.Run(); err != nil {
		return fmt.Errorf("git add failed: %w", err)
	}

	// Check if there are changes to commit
	statusCmd := exec.Command("git", "diff", "--cached", "--quiet")
	if err := statusCmd.Run(); err == nil {
		fmt.Println("No changes to commit.")
		return nil
	}

	// Git commit
	commitMsg := fmt.Sprintf("docs: update %s project list [skip ci]", orgName)
	fmt.Printf("Running: git commit -m \"%s\"\n", commitMsg)
	commitCmd := exec.Command("git", "commit", "-m", commitMsg)
	commitCmd.Stdout = os.Stdout
	commitCmd.Stderr = os.Stderr
	if err := commitCmd.Run(); err != nil {
		return fmt.Errorf("git commit failed: %w", err)
	}

	// Git push
	fmt.Println("Running: git push")
	pushCmd := exec.Command("git", "push")
	pushCmd.Stdout = os.Stdout
	pushCmd.Stderr = os.Stderr
	if err := pushCmd.Run(); err != nil {
		return fmt.Errorf("git push failed: %w", err)
	}

	fmt.Println("Successfully committed and pushed changes.")
	return nil
}

func init() {
	GitCmd.AddCommand(updateOrgStatusCmd)

	updateOrgStatusCmd.Flags().StringVarP(&updateOrgStatusOutput, "output", "o", ".github/README.md", "Output path for the README file")
	updateOrgStatusCmd.Flags().BoolVar(&updateOrgStatusDryRun, "dry-run", false, "Print README content without writing to file")
}
