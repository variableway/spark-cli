package github

import (
	"testing"
)

func TestParseAccountFromURL(t *testing.T) {
	tests := []struct {
		name    string
		url     string
		want    string
		wantErr bool
	}{
		{
			name:    "simple account name",
			url:     "variableway",
			want:    "variableway",
			wantErr: false,
		},
		{
			name:    "github URL with https",
			url:     "https://github.com/variableway",
			want:    "variableway",
			wantErr: false,
		},
		{
			name:    "github URL with trailing slash",
			url:     "https://github.com/variableway/",
			want:    "variableway",
			wantErr: false,
		},
		{
			name:    "github URL with account and extra path",
			url:     "https://github.com/variableway/repos",
			want:    "variableway",
			wantErr: false,
		},
		{
			name:    "personal account URL",
			url:     "https://github.com/jackwener",
			want:    "jackwener",
			wantErr: false,
		},
		{
			name:    "invalid URL",
			url:     "https://example.com/variableway",
			want:    "",
			wantErr: true,
		},
		{
			name:    "empty string",
			url:     "",
			want:    "",
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := ParseAccountFromURL(tt.url)
			if (err != nil) != tt.wantErr {
				t.Errorf("ParseAccountFromURL() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if got != tt.want {
				t.Errorf("ParseAccountFromURL() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestRepositorySorting(t *testing.T) {
	repos := []Repository{
		{Name: "repo-c", Stargazers: 10},
		{Name: "repo-a", Stargazers: 100},
		{Name: "repo-b", Stargazers: 50},
	}

	// Sort by stargazers count (descending)
	for i := 0; i < len(repos)-1; i++ {
		for j := i + 1; j < len(repos); j++ {
			if repos[i].Stargazers < repos[j].Stargazers {
				repos[i], repos[j] = repos[j], repos[i]
			}
		}
	}

	// Check order
	if repos[0].Name != "repo-a" || repos[0].Stargazers != 100 {
		t.Errorf("Expected first repo to be repo-a with 100 stars, got %s with %d stars", repos[0].Name, repos[0].Stargazers)
	}
	if repos[1].Name != "repo-b" || repos[1].Stargazers != 50 {
		t.Errorf("Expected second repo to be repo-b with 50 stars, got %s with %d stars", repos[1].Name, repos[1].Stargazers)
	}
	if repos[2].Name != "repo-c" || repos[2].Stargazers != 10 {
		t.Errorf("Expected third repo to be repo-c with 10 stars, got %s with %d stars", repos[2].Name, repos[2].Stargazers)
	}
}
