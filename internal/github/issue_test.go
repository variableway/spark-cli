package github

import (
	"os"
	"path/filepath"
	"testing"
)

func TestExtractTitle(t *testing.T) {
	tests := []struct {
		name     string
		content  string
		filename string
		want     string
	}{
		{
			name:     "extract from h1 heading",
			content:  "# My Issue Title\n\nSome body content",
			filename: "issue.md",
			want:     "My Issue Title",
		},
		{
			name:     "fallback to filename without extension",
			content:  "No heading here\nJust body text",
			filename: "my-issue.md",
			want:     "my-issue",
		},
		{
			name:     "skip h2 heading",
			content:  "## This is h2\n# This is h1",
			filename: "test.md",
			want:     "This is h1",
		},
		{
			name:     "heading with leading spaces",
			content:  "  # Trimmed Title\nBody",
			filename: "test.md",
			want:     "Trimmed Title",
		},
		{
			name:     "empty file uses filename",
			content:  "",
			filename: "empty-doc.md",
			want:     "empty-doc",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := extractTitle(tt.content, tt.filename)
			if got != tt.want {
				t.Errorf("extractTitle() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestReadDocsAsIssues(t *testing.T) {
	dir := t.TempDir()

	t.Run("reads markdown files as issues", func(t *testing.T) {
		os.WriteFile(filepath.Join(dir, "issue1.md"), []byte("# First Issue\n\nBody of first issue"), 0644)
		os.WriteFile(filepath.Join(dir, "issue2.md"), []byte("# Second Issue\n\nBody of second issue"), 0644)

		issues, err := ReadDocsAsIssues(dir)
		if err != nil {
			t.Fatalf("ReadDocsAsIssues() error = %v", err)
		}
		if len(issues) != 2 {
			t.Fatalf("expected 2 issues, got %d", len(issues))
		}

		titles := map[string]bool{issues[0].Title: true, issues[1].Title: true}
		if !titles["First Issue"] || !titles["Second Issue"] {
			t.Errorf("expected titles 'First Issue' and 'Second Issue', got %q and %q", issues[0].Title, issues[1].Title)
		}
	})

	t.Run("returns error for empty directory", func(t *testing.T) {
		emptyDir := t.TempDir()
		_, err := ReadDocsAsIssues(emptyDir)
		if err == nil {
			t.Error("expected error for empty directory")
		}
	})

	t.Run("ignores non-markdown files", func(t *testing.T) {
		mixedDir := t.TempDir()
		os.WriteFile(filepath.Join(mixedDir, "doc.md"), []byte("# Doc\nContent"), 0644)
		os.WriteFile(filepath.Join(mixedDir, "ignore.txt"), []byte("Not a doc"), 0644)

		issues, err := ReadDocsAsIssues(mixedDir)
		if err != nil {
			t.Fatalf("ReadDocsAsIssues() error = %v", err)
		}
		if len(issues) != 1 {
			t.Fatalf("expected 1 issue, got %d", len(issues))
		}
		if issues[0].Title != "Doc" {
			t.Errorf("expected title 'Doc', got %q", issues[0].Title)
		}
	})
}
