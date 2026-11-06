package github

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strings"
)

type Repository struct {
	Name        string   `json:"name"`
	FullName    string   `json:"full_name"`
	HTMLURL     string   `json:"html_url"`
	SSHURL      string   `json:"ssh_url"`
	CloneURL    string   `json:"clone_url"`
	Private     bool     `json:"private"`
	Fork        bool     `json:"fork"`
	Description string   `json:"description"`
	Stargazers  int      `json:"stargazers_count"`
	Language    string   `json:"language"`
	Topics      []string `json:"topics"`
	Homepage    string   `json:"homepage"`
	CreatedAt   string   `json:"created_at"`
	PushedAt    string   `json:"pushed_at"`
	Owner       struct {
		Login string `json:"login"`
	} `json:"owner"`
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

// getJSON performs a GET request against the GitHub API, attaching the
// GITHUB_TOKEN credential when available to raise the rate limit.
func getJSON(url string, out interface{}) error {
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("Accept", "application/vnd.github+json")
	// The GitHub API rejects requests without a User-Agent; some gateways
	// answer them with 504 instead of 403, so always send one.
	req.Header.Set("User-Agent", "spark-cli")
	if token := os.Getenv("GITHUB_TOKEN"); token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return fmt.Errorf("fetch %s: %w", url, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("fetch %s: HTTP %d", url, resp.StatusCode)
	}

	return json.NewDecoder(resp.Body).Decode(out)
}

// listRepos fetches every page of a repository listing endpoint.
func listRepos(baseURL string) ([]Repository, error) {
	const perPage = 100

	var all []Repository
	for page := 1; ; page++ {
		var batch []Repository
		url := fmt.Sprintf("%s?per_page=%d&page=%d", baseURL, perPage, page)
		if err := getJSON(url, &batch); err != nil {
			if strings.Contains(err.Error(), "HTTP 404") {
				return nil, err
			}
			return nil, fmt.Errorf("failed to fetch repositories: %w", err)
		}
		all = append(all, batch...)
		if len(batch) < perPage {
			break
		}
	}

	return all, nil
}

func GetOrgRepos(orgName string) ([]Repository, error) {
	url := fmt.Sprintf("https://api.github.com/orgs/%s/repos", orgName)

	repos, err := listRepos(url)
	if err != nil {
		if strings.Contains(err.Error(), "HTTP 404") {
			return nil, fmt.Errorf("organization '%s' not found", orgName)
		}
		return nil, err
	}

	return repos, nil
}

func GetUserRepos(username string) ([]Repository, error) {
	url := fmt.Sprintf("https://api.github.com/users/%s/repos", username)

	repos, err := listRepos(url)
	if err != nil {
		if strings.Contains(err.Error(), "HTTP 404") {
			return nil, fmt.Errorf("user '%s' not found", username)
		}
		return nil, err
	}

	return repos, nil
}

func GetRepo(owner, repo string) (*Repository, error) {
	url := fmt.Sprintf("https://api.github.com/repos/%s/%s", owner, repo)

	var r Repository
	if err := getJSON(url, &r); err != nil {
		if strings.Contains(err.Error(), "HTTP 404") {
			return nil, fmt.Errorf("repository '%s/%s' not found", owner, repo)
		}
		return nil, fmt.Errorf("fetch repository: %w", err)
	}
	return &r, nil
}

func DetectAccountType(name string) (AccountType, error) {
	url := fmt.Sprintf("https://api.github.com/users/%s", name)

	var userInfo struct {
		Type string `json:"type"`
	}
	if err := getJSON(url, &userInfo); err != nil {
		if strings.Contains(err.Error(), "HTTP 404") {
			return "", fmt.Errorf("account '%s' not found", name)
		}
		return "", fmt.Errorf("failed to detect account type: %w", err)
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
