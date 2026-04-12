package github

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

type IssueInput struct {
	Title string
	Body  string
}

func CreateIssue(repo, title, body string, labels []string) error {
	args := []string{"issue", "create", "--repo", repo, "--title", title, "--body", body}
	for _, label := range labels {
		args = append(args, "--label", label)
	}

	cmd := exec.Command("gh", args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to create issue '%s': %w", title, err)
	}

	return nil
}

func ReadDocsAsIssues(dir string) ([]IssueInput, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, fmt.Errorf("failed to read directory '%s': %w", dir, err)
	}

	var issues []IssueInput
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}

		name := entry.Name()
		if !strings.HasSuffix(strings.ToLower(name), ".md") {
			continue
		}

		filePath := filepath.Join(dir, name)
		content, err := os.ReadFile(filePath)
		if err != nil {
			return nil, fmt.Errorf("failed to read file '%s': %w", filePath, err)
		}

		body := string(content)
		title := extractTitle(body, name)

		issues = append(issues, IssueInput{
			Title: title,
			Body:  body,
		})
	}

	if len(issues) == 0 {
		return nil, fmt.Errorf("no markdown files found in '%s'", dir)
	}

	return issues, nil
}

func extractTitle(content, filename string) string {
	lines := strings.Split(content, "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "# ") {
			return strings.TrimSpace(strings.TrimPrefix(line, "#"))
		}
	}

	ext := filepath.Ext(filename)
	return strings.TrimSuffix(filename, ext)
}
