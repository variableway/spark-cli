package github

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
)

type Repository struct {
	Name        string `json:"name"`
	FullName    string `json:"full_name"`
	HTMLURL     string `json:"html_url"`
	SSHURL      string `json:"ssh_url"`
	CloneURL    string `json:"clone_url"`
	Private     bool   `json:"private"`
	Fork        bool   `json:"fork"`
	Description string `json:"description"`
	Stargazers  int    `json:"stargazers_count"`
	Language    string `json:"language"`
}

type OrgReposResponse []Repository

func GetOrgRepos(orgName string) ([]Repository, error) {
	url := fmt.Sprintf("https://api.github.com/orgs/%s/repos?per_page=100", orgName)
	
	resp, err := http.Get(url)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch repositories: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNotFound {
		return nil, fmt.Errorf("organization '%s' not found", orgName)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("failed to fetch repositories: HTTP %d", resp.StatusCode)
	}

	var repos OrgReposResponse
	if err := json.NewDecoder(resp.Body).Decode(&repos); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	return repos, nil
}

func ParseOrgFromURL(url string) (string, error) {
	url = strings.TrimSpace(url)
	url = strings.TrimSuffix(url, "/")

	if url == "" {
		return "", fmt.Errorf("organization name or URL cannot be empty")
	}

	if strings.Contains(url, "github.com/") {
		parts := strings.Split(url, "github.com/")
		if len(parts) > 1 {
			org := strings.Split(parts[1], "/")[0]
			if org != "" {
				return org, nil
			}
		}
	}

	if !strings.Contains(url, "/") && !strings.Contains(url, "http") {
		return url, nil
	}

	return "", fmt.Errorf("could not parse organization from URL: %s", url)
}
