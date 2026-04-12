package git

import (
	"fmt"
	"spark/internal/github"
	"strings"

	"github.com/pterm/pterm"
	"github.com/spf13/cobra"
)

var (
	batchIssueDocs   string
	batchIssueDryRun bool
	batchIssueLabels string
)

var batchIssueCmd = &cobra.Command{
	Use:   "batch-issue <repo>",
	Short: "Create GitHub issues from a folder of markdown documents",
	Long: `Create GitHub issues from a folder of markdown documents.

Each markdown file becomes one GitHub issue:
- Title: extracted from the first "# heading" in the file, or the filename if no heading found
- Body: the full content of the document

Requires gh CLI to be installed and authenticated.`,
	Args: cobra.ExactArgs(1),
	Example: `  spark git batch-issue variableway/spark-cli -d ./docs
  spark git batch-issue owner/repo -d ./issues --dry-run
  spark git batch-issue owner/repo -d ./docs --label "documentation"`,
	RunE: func(cmd *cobra.Command, args []string) error {
		repo := args[0]

		issues, err := github.ReadDocsAsIssues(batchIssueDocs)
		if err != nil {
			return err
		}

		var labels []string
		if batchIssueLabels != "" {
			labels = splitLabels(batchIssueLabels)
		}

		fmt.Printf("Found %d documents in '%s'\n\n", len(issues), batchIssueDocs)

		if batchIssueDryRun {
			pterm.Info.Println("Dry run mode - previewing issues:")
			fmt.Println()
			for i, issue := range issues {
				fmt.Printf("[%d/%d] %s\n", i+1, len(issues), issue.Title)
				fmt.Printf("  Labels: %v\n", labels)
				fmt.Printf("  Body length: %d chars\n\n", len(issue.Body))
			}
			return nil
		}

		successCount := 0
		failCount := 0

		for i, issue := range issues {
			fmt.Printf("[%d/%d] Creating issue: %s\n", i+1, len(issues), issue.Title)

			if err := github.CreateIssue(repo, issue.Title, issue.Body, labels); err != nil {
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
	},
}

func splitLabels(labelStr string) []string {
	var result []string
	for _, l := range strings.Split(labelStr, ",") {
		l = strings.TrimSpace(l)
		if l != "" {
			result = append(result, l)
		}
	}
	return result
}

func init() {
	GitCmd.AddCommand(batchIssueCmd)

	batchIssueCmd.Flags().StringVarP(&batchIssueDocs, "docs", "d", ".", "Folder containing markdown documents")
	batchIssueCmd.Flags().BoolVar(&batchIssueDryRun, "dry-run", false, "Preview issues without creating them")
	batchIssueCmd.Flags().StringVarP(&batchIssueLabels, "label", "l", "", "Labels to add to all issues (comma-separated)")
}
