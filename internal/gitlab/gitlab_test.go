package gitlab

import (
	"testing"
)

func TestIsGitLabURL(t *testing.T) {
	tests := []struct {
		input string
		want  bool
	}{
		{"https://git.cew.io/carbonnt/cyacle/domain", true},
		{"https://gitlab.com/mygroup/myproject", true},
		{"http://git.example.com/group", true},
		{"https://github.com/owner/repo", false},
		{"variableway", false},
		{"", false},
		{"github.com/owner", false},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got := IsGitLabURL(tt.input)
			if got != tt.want {
				t.Errorf("IsGitLabURL(%q) = %v, want %v", tt.input, got, tt.want)
			}
		})
	}
}

func TestParseGitLabURL(t *testing.T) {
	tests := []struct {
		name      string
		input     string
		wantBase  string
		wantGroup string
		wantErr   bool
	}{
		{
			name:      "self-hosted nested group",
			input:     "https://git.cew.io/carbonnt/cyacle/domain",
			wantBase:  "https://git.cew.io",
			wantGroup: "carbonnt/cyacle/domain",
		},
		{
			name:      "gitlab.com project",
			input:     "https://gitlab.com/mygroup/myproject",
			wantBase:  "https://gitlab.com",
			wantGroup: "mygroup/myproject",
		},
		{
			name:      "single group",
			input:     "http://git.example.com/group",
			wantBase:  "http://git.example.com",
			wantGroup: "group",
		},
		{
			name:      "with trailing slash",
			input:     "https://git.cew.io/carbonnt/cyacle/domain/",
			wantBase:  "https://git.cew.io",
			wantGroup: "carbonnt/cyacle/domain",
		},
		{
			name:    "no path",
			input:   "https://git.cew.io/",
			wantErr: true,
		},
		{
			name:    "empty path",
			input:   "https://git.cew.io",
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gotBase, gotGroup, err := ParseGitLabURL(tt.input)
			if (err != nil) != tt.wantErr {
				t.Errorf("ParseGitLabURL(%q) error = %v, wantErr %v", tt.input, err, tt.wantErr)
				return
			}
			if gotBase != tt.wantBase {
				t.Errorf("ParseGitLabURL(%q) baseURL = %q, want %q", tt.input, gotBase, tt.wantBase)
			}
			if gotGroup != tt.wantGroup {
				t.Errorf("ParseGitLabURL(%q) groupPath = %q, want %q", tt.input, gotGroup, tt.wantGroup)
			}
		})
	}
}

func TestExtractHost(t *testing.T) {
	tests := []struct {
		input string
		want  string
	}{
		{"https://git.cew.io", "git.cew.io"},
		{"https://gitlab.com", "gitlab.com"},
		{"http://git.example.com:8080", "git.example.com:8080"},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got := extractHost(tt.input)
			if got != tt.want {
				t.Errorf("extractHost(%q) = %q, want %q", tt.input, got, tt.want)
			}
		})
	}
}
