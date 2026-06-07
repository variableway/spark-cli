package git

import "testing"

func TestParseRepoSlug(t *testing.T) {
	tests := []struct {
		input   string
		want    string
		wantErr bool
	}{
		{"https://github.com/Nutlope/pdf-to-interactive-lesson.git", "Nutlope/pdf-to-interactive-lesson", false},
		{"https://github.com/owner/repo", "owner/repo", false},
		{"http://github.com/owner/repo.git", "owner/repo", false},
		{"git@github.com:owner/repo.git", "owner/repo", false},
		{"github.com/owner/repo", "owner/repo", false},
		{"owner/repo", "owner/repo", false},
		{"owner/repo/", "owner/repo", false},
		{"https://www.github.com/owner/repo.git", "owner/repo", false},
		{"invalid-url", "", true},
		{"", "", true},
		{"https://github.com/", "", true},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got, err := parseRepoSlug(tt.input)
			if (err != nil) != tt.wantErr {
				t.Errorf("parseRepoSlug(%q) error = %v, wantErr %v", tt.input, err, tt.wantErr)
				return
			}
			if got != tt.want {
				t.Errorf("parseRepoSlug(%q) = %q, want %q", tt.input, got, tt.want)
			}
		})
	}
}
