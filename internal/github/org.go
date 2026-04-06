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

type AccountType string

const (
	AccountTypeOrg  AccountType = "org"
	AccountTypeUser AccountType = "user"
)

type AccountInfo struct {
	Type AccountType
	Name string
}

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

	var repos []Repository
	if err := json.NewDecoder(resp.Body).Decode(&repos); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	return repos, nil
}

func GetUserRepos(username string) ([]Repository, error) {
	url := fmt.Sprintf("https://api.github.com/users/%s/repos?per_page=100", username)
	
	resp, err := http.Get(url)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch repositories: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNotFound {
		return nil, fmt.Errorf("user '%s' not found", username)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("failed to fetch repositories: HTTP %d", resp.StatusCode)
	}

	var repos []Repository
	if err := json.NewDecoder(resp.Body).Decode(&repos); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	return repos, nil
}

func DetectAccountType(name string) (AccountType, error) {
	url := fmt.Sprintf("https://api.github.com/users/%s", name)
	
	resp, err := http.Get(url)
	if err != nil {
		return "", fmt.Errorf("failed to detect account type: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNotFound {
		return "", fmt.Errorf("account '%s' not found", name)
	}

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("failed to detect account type: HTTP %d", resp.StatusCode)
	}

	var userInfo struct {
		Type string `json:"type"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&userInfo); err != nil {
		return "", fmt.Errorf("failed to parse response: %w", err)
	}

	switch userInfo.Type {
	case "Organization":
		return AccountTypeOrg, nil
	case "User":
		return AccountTypeUser, nil
	default:
		return "", fmt.Errorf("unknown account type: %s", userInfo.Type)
	}
}

func GetReposForAccount(name string) ([]Repository, AccountType, error) {
	accountType, err := DetectAccountType(name)
	if err != nil {
		return nil, "", err
	}

	var repos []Repository
	switch accountType {
	case AccountTypeOrg:
		repos, err = GetOrgRepos(name)
	case AccountTypeUser:
		repos, err = GetUserRepos(name)
	}

	if err != nil {
		return nil, "", err
	}

	return repos, accountType, nil
}

func ParseAccountFromURL(url string) (string, error) {
	url = strings.TrimSpace(url)
	url = strings.TrimSuffix(url, "/")

	if url == "" {
		return "", fmt.Errorf("account name or URL cannot be empty")
	}

	if strings.Contains(url, "github.com/") {
		parts := strings.Split(url, "github.com/")
		if len(parts) > 1 {
			account := strings.Split(parts[1], "/")[0]
			if account != "" {
				return account, nil
			}
		}
	}

	if !strings.Contains(url, "/") && !strings.Contains(url, "http") {
		return url, nil
	}

	return "", fmt.Errorf("could not parse account from URL: %s", url)
}
