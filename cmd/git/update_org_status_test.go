package git

import (
	"strings"
	"testing"

	"monolize/internal/github"
)

func TestGenerateREADME(t *testing.T) {
	repos := []github.Repository{
		{
			Name:        "spark-cli",
			HTMLURL:     "https://github.com/variableway/spark-cli",
			Description: "A CLI tool for managing multiple git repositories",
			Stargazers:  42,
			Language:    "Go",
			Fork:        false,
		},
		{
			Name:        "spark-skills",
			HTMLURL:     "https://github.com/variableway/spark-skills",
			Description: "AI Agent skills collection",
			Stargazers:  15,
			Language:    "Python",
			Fork:        false,
		},
		{
			Name:        "forked-repo",
			HTMLURL:     "https://github.com/variableway/forked-repo",
			Description: "A forked repository",
			Stargazers:  100,
			Language:    "JavaScript",
			Fork:        true, // Should be skipped
		},
	}

	content := generateREADME("variableway", repos)

	// Check header
	if !strings.Contains(content, "# Variableway Projects") {
		t.Error("README should contain organization title")
	}

	// Check table header
	if !strings.Contains(content, "| Name | Description | Stars | Language |") {
		t.Error("README should contain table header")
	}

	// Check repo links
	if !strings.Contains(content, "[spark-cli](https://github.com/variableway/spark-cli)") {
		t.Error("README should contain spark-cli link")
	}

	// Check stars
	if !strings.Contains(content, "⭐ 42") {
		t.Error("README should contain star count")
	}

	// Check statistics section
	if !strings.Contains(content, "Total Repositories") {
		t.Error("README should contain statistics section")
	}

	// Forked repo should not be in the list
	if strings.Contains(content, "forked-repo") {
		t.Error("Forked repositories should not be included in the README")
	}

	// Check language display
	if !strings.Contains(content, "Go") || !strings.Contains(content, "Python") {
		t.Error("README should contain language information")
	}
}

func TestGenerateREADMEWithEmptyDescription(t *testing.T) {
	repos := []github.Repository{
		{
			Name:        "empty-desc-repo",
			HTMLURL:     "https://github.com/variableway/empty-desc-repo",
			Description: "",
			Stargazers:  5,
			Language:    "",
			Fork:        false,
		},
	}

	content := generateREADME("variableway", repos)

	// Check that empty description is replaced with "-"
	if !strings.Contains(content, "| - |") {
		t.Error("Empty description should be displayed as '-'")
	}

	// Check that empty language is replaced with "-"
	lines := strings.Split(content, "\n")
	for _, line := range lines {
		if strings.Contains(line, "empty-desc-repo") {
			if !strings.Contains(line, "|") {
				continue
			}
			// The line should contain "-" for language
			parts := strings.Split(line, "|")
			if len(parts) >= 5 {
				lang := strings.TrimSpace(parts[4])
				if lang != "-" && lang != "" {
					t.Errorf("Empty language should be displayed as '-', got '%s'", lang)
				}
			}
		}
	}
}

func TestGenerateREADMEStatistics(t *testing.T) {
	repos := []github.Repository{
		{Name: "repo1", Stargazers: 100, Fork: false},
		{Name: "repo2", Stargazers: 50, Fork: false},
		{Name: "repo3", Stargazers: 25, Fork: true}, // Fork, won't count
	}

	content := generateREADME("testorg", repos)

	// Check total repositories
	if !strings.Contains(content, "**Total Repositories**: 3") {
		t.Error("README should show total repositories count")
	}

	// Check non-fork count
	if !strings.Contains(content, "**Non-fork Repositories**: 2") {
		t.Error("README should show non-fork repositories count")
	}

	// Check total stars (only non-fork)
	if !strings.Contains(content, "**Total Stars**: 150") {
		t.Error("README should show total stars (150 = 100 + 50)")
	}

	// Check average stars
	if !strings.Contains(content, "**Average Stars**: 75.0") {
		t.Error("README should show average stars (75.0 = 150 / 2)")
	}
}
