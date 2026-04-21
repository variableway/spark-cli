package git

import (
	"fmt"
	"spark/internal/git"
	"spark/internal/github"
	"strings"

	"github.com/pterm/pterm"
	"github.com/spf13/cobra"
)

var (
	issuesRepo   string
	issuesFile   string
	issuesDir    string
	issuesLabels []string
	issuesDryRun bool
)

var issuesCmd = &cobra.Command{
	Use:   "issues",
	Short: "Create GitHub issues from markdown files or tasks",
	Long: `Create GitHub issues from markdown files or tasks.

This command supports two modes:

1. Batch mode (folder): Create issues from all markdown files in a directory
   spark git issues -d ./docs

2. Task mode (single file): Create issues from tasks in a markdown file
   spark git issues -f tasks.md

The repository can be specified with -r flag or auto-detected from the current git repo.

Examples:
  # Create issues from all markdown files in a folder
  spark git issues -d ./docs

  # Create issues from tasks in a single file
  spark git issues -f tasks/features/my-feature.md

  # Specify repo explicitly
  spark git issues -r owner/repo -d ./docs

  # Create with labels
  spark git issues -d ./docs -l bug,enhancement

  # Preview without creating
  spark git issues -d ./docs --dry-run`,
	Args: cobra.NoArgs,
	RunE: func(cmd *cobra.Command, args []string) error {
		// Determine repository
		repo := issuesRepo
		if repo == "" {
			var err error
			repo, err = getCurrentRepo()
			if err != nil {
				return fmt.Errorf("repository is required. Use -r flag or run from within a git repository with GitHub remote: %w", err)
			}
		}

		// Validate that we have either -d or -f
		if issuesDir == "" && issuesFile == "" {
			return fmt.Errorf("either -d (directory) or -f (file) flag is required")
		}
		if issuesDir != "" && issuesFile != "" {
			return fmt.Errorf("cannot use both -d and -f flags at the same time")
		}

		if issuesFile != "" {
			return createIssuesFromTasks(repo)
		}
		return createIssuesFromDir(repo)
	},
}

func getCurrentRepo() (string, error) {
	remoteURL, err := git.GetRemoteURL(".")
	if err != nil {
		return "", err
	}

	// Parse owner/repo from remote URL
	// Handles: https://github.com/owner/repo.git or git@github.com:owner/repo.git
	repo := extractRepoFromURL(remoteURL)
	if repo == "" {
		return "", fmt.Errorf("could not extract owner/repo from remote URL: %s", remoteURL)
	}
	return repo, nil
}

func extractRepoFromURL(url string) string {
	url = strings.TrimSuffix(url, ".git")

	// Handle HTTPS: https://github.com/owner/repo
	if strings.Contains(url, "://") {
		parts := strings.Split(url, "/")
		if len(parts) >= 2 {
			return parts[len(parts)-2] + "/" + parts[len(parts)-1]
		}
	}

	// Handle SSH: git@github.com:owner/repo
	if strings.Contains(url, ":") {
		parts := strings.Split(url, ":")
		if len(parts) >= 2 {
			path := parts[len(parts)-1]
			pathParts := strings.Split(path, "/")
			if len(pathParts) >= 2 {
				return pathParts[len(pathParts)-2] + "/" + pathParts[len(pathParts)-1]
			}
		}
	}

	return ""
}

func createIssuesFromTasks(repo string) error {
	if issuesFile == "" {
		return fmt.Errorf("file path is required for task mode, use -f flag")
	}

	creator := github.NewMarkdownIssueCreator(repo)

	if issuesDryRun {
		return previewTasks(creator, issuesFile)
	}

	fmt.Printf("Creating issues from tasks in %s to repository %s...\n\n", issuesFile, repo)

	if err := creator.CreateIssuesFromFile(issuesFile, issuesLabels); err != nil {
		return err
	}

	fmt.Println("\n✓ All issues created successfully!")
	return nil
}

func createIssuesFromDir(repo string) error {
	if issuesDir == "" {
		issuesDir = "."
	}

	issues, err := github.ReadDocsAsIssues(issuesDir)
	if err != nil {
		return err
	}

	fmt.Printf("Found %d documents in '%s'\n\n", len(issues), issuesDir)

	if issuesDryRun {
		pterm.Info.Println("Dry run mode - previewing issues:")
		fmt.Println()
		for i, issue := range issues {
			fmt.Printf("[%d/%d] %s\n", i+1, len(issues), issue.Title)
			fmt.Printf("  Labels: %v\n", issuesLabels)
			fmt.Printf("  Body length: %d chars\n\n", len(issue.Body))
		}
		return nil
	}

	successCount := 0
	failCount := 0

	for i, issue := range issues {
		fmt.Printf("[%d/%d] Creating issue: %s\n", i+1, len(issues), issue.Title)

		if err := github.CreateIssue(repo, issue.Title, issue.Body, issuesLabels); err != nil {
			pterm.Error.Printf("Failed: %v\n", err)
			failCount++
		} else {
			pterm.Success.Printf("Created: %s\n", issue.Title)
			successCount++
		}
	}

	fmt.Printf("\n--- Summary ---\n")
	fmt.Printf("Created: %d\n", successCount)
	fmt.Printf("Failed: %d\n", failCount)

	return nil
}

func previewTasks(creator *github.MarkdownIssueCreator, filePath string) error {
	tasks, err := creator.PreviewTasks(filePath)
	if err != nil {
		return err
	}

	if len(tasks) == 0 {
		fmt.Println("No tasks found in the file.")
		fmt.Println("Expected format: ## Task <id>: <title>")
		return nil
	}

	fmt.Printf("Found %d task(s) in %s:\n\n", len(tasks), filePath)
	for _, task := range tasks {
		fmt.Printf("Task %s: %s\n", task.ID, task.Title)
		if task.Content != "" {
			content := task.Content
			if len(content) > 100 {
				content = content[:100] + "..."
			}
			fmt.Printf("  Content: %s\n", content)
		}
		fmt.Println()
	}

	return nil
}

func init() {
	issuesCmd.Flags().StringVarP(&issuesRepo, "repo", "r", "", "Target repository (format: owner/repo)")
	issuesCmd.Flags().StringVarP(&issuesFile, "file", "f", "", "Path to markdown file containing tasks")
	issuesCmd.Flags().StringVarP(&issuesDir, "dir", "d", "", "Path to directory containing markdown documents")
	issuesCmd.Flags().StringSliceVarP(&issuesLabels, "labels", "l", []string{}, "Comma-separated list of labels to apply")
	issuesCmd.Flags().BoolVar(&issuesDryRun, "dry-run", false, "Preview without creating issues")

	GitCmd.AddCommand(issuesCmd)
}
