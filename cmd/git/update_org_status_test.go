package git

import (
	"strings"
	"testing"

	"monolize/internal/github"
)

func TestGenerateProjectListSection(t *testing.T) {
	// Set section name for testing
	updateOrgStatusSection = "Project List"

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

	content := generateProjectListSection("variableway", repos)

	// Check section header
	if !strings.Contains(content, "## Project List") {
		t.Error("Section should contain '## Project List' header")
	}

	// Check table header
	if !strings.Contains(content, "| Name | Description | Stars | Language |") {
		t.Error("Section should contain table header")
	}

	// Check repo links
	if !strings.Contains(content, "[spark-cli](https://github.com/variableway/spark-cli)") {
		t.Error("Section should contain spark-cli link")
	}

	// Check stars
	if !strings.Contains(content, "⭐ 42") {
		t.Error("Section should contain star count")
	}

	// Check timestamp
	if !strings.Contains(content, "*Last updated:") {
		t.Error("Section should contain timestamp")
	}

	// Check statistics
	if !strings.Contains(content, "**Statistics**:") {
		t.Error("Section should contain statistics")
	}

	// Forked repo should not be in the list
	if strings.Contains(content, "forked-repo") {
		t.Error("Forked repositories should not be included")
	}

	// Check language display
	if !strings.Contains(content, "Go") || !strings.Contains(content, "Python") {
		t.Error("Section should contain language information")
	}
}

func TestGenerateProjectListSectionWithEmptyFields(t *testing.T) {
	updateOrgStatusSection = "Project List"

	repos := []github.Repository{
		{
			Name:        "empty-repo",
			HTMLURL:     "https://github.com/variableway/empty-repo",
			Description: "",
			Stargazers:  5,
			Language:    "",
			Fork:        false,
		},
	}

	content := generateProjectListSection("variableway", repos)

	// Check that empty description is replaced with "-"
	if !strings.Contains(content, "| - | ⭐ 5 | - |") && !strings.Contains(content, "| - |") {
		// The exact format may vary, but there should be "-" for empty fields
		if !strings.Contains(content, "| - |") {
			t.Error("Empty description and language should be displayed as '-'")
		}
	}
}

func TestUpdateSectionInContent(t *testing.T) {
	tests := []struct {
		name        string
		existing    string
		newSection  string
		sectionName string
		wantContain []string
		wantNotContain []string
	}{
		{
			name: "update existing section",
			existing: `# Test Org

## Introduction
Some intro text.

## Project List
Old content here.

## Footer
Footer text.`,
			newSection:  "## Project List\n\nNew content here.\n",
			sectionName: "Project List",
			wantContain: []string{
				"## Introduction",
				"Some intro text.",
				"## Project List",
				"New content here.",
				"## Footer",
				"Footer text.",
			},
			wantNotContain: []string{"Old content here."},
		},
		{
			name: "add new section when not exists",
			existing: `# Test Org

## Introduction
Some intro text.

## Footer
Footer text.`,
			newSection:  "## Project List\n\nNew content here.\n",
			sectionName: "Project List",
			wantContain: []string{
				"## Introduction",
				"## Project List",
				"New content here.",
				"## Footer",
			},
		},
		{
			name: "update section at end of file",
			existing: `# Test Org

## Project List
Old content.`,
			newSection:  "## Project List\n\nNew content here.\n",
			sectionName: "Project List",
			wantContain: []string{
				"## Project List",
				"New content here.",
			},
			wantNotContain: []string{"Old content."},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := updateSectionInContent(tt.existing, tt.newSection, tt.sectionName)

			for _, want := range tt.wantContain {
				if !strings.Contains(result, want) {
					t.Errorf("Expected result to contain %q, but it didn't.\nResult:\n%s", want, result)
				}
			}

			for _, notWant := range tt.wantNotContain {
				if strings.Contains(result, notWant) {
					t.Errorf("Expected result NOT to contain %q, but it did.\nResult:\n%s", notWant, result)
				}
			}
		})
	}
}

func TestUpdateSectionInContentComplex(t *testing.T) {
	// Test that section with special characters in content is preserved
	existing := `# Organization

## Project List
| Name | Desc |
|------|------|
| old | repo |

## References
Some refs.`

	newSection := "## Project List\n\n| Name | Desc |\n|------|------|\n| new | repo |\n"

	result := updateSectionInContent(existing, newSection, "Project List")

	// Should have new content
	if !strings.Contains(result, "| new | repo |") {
		t.Error("Should contain new repo")
	}

	// Should not have old content
	if strings.Contains(result, "| old | repo |") {
		t.Error("Should not contain old repo")
	}

	// Should preserve other sections
	if !strings.Contains(result, "## References") {
		t.Error("Should preserve References section")
	}
}

func TestGenerateFullREADME(t *testing.T) {
	sectionContent := "## Project List\n\nSome projects here.\n"
	content := generateFullREADME("testorg", sectionContent)

	if !strings.Contains(content, "# Testorg") {
		t.Error("Should contain title")
	}

	if !strings.Contains(content, "Welcome to **testorg**!") {
		t.Error("Should contain welcome message")
	}

	if !strings.Contains(content, "## Project List") {
		t.Error("Should contain section content")
	}
}

func TestSectionNameCustom(t *testing.T) {
	// Test with custom section name
	updateOrgStatusSection = "My Projects"

	repos := []github.Repository{
		{Name: "repo1", HTMLURL: "https://github.com/test/repo1", Stargazers: 10, Fork: false},
	}

	content := generateProjectListSection("test", repos)

	if !strings.Contains(content, "## My Projects") {
		t.Error("Should use custom section name")
	}

	// Reset to default
	updateOrgStatusSection = "Project List"
}
