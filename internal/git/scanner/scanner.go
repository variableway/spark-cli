package scanner

import (
	"bufio"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

type gitHubAPIResponse struct {
	Description string `json:"description"`
	Stargazers  int    `json:"stargazers_count"`
	Forks       int    `json:"forks_count"`
	Language    string `json:"language"`
	UpdatedAt   string `json:"updated_at"`
}

type gitLabAPIResponse struct {
	Description string `json:"description"`
	StarCount   int    `json:"star_count"`
	ForksCount  int    `json:"forks_count"`
}

func Scan(rootPath string, opts Options) ([]RepoInfo, error) {
	absPath, err := filepath.Abs(rootPath)
	if err != nil {
		return nil, fmt.Errorf("resolve path: %w", err)
	}

	repos := scanForRepos(absPath)
	if len(repos) == 0 {
		return repos, nil
	}

	if !opts.SkipAPI {
		for i := range repos {
			fetchRepoInfo(&repos[i])
			time.Sleep(100 * time.Millisecond)
		}
	}

	return repos, nil
}

func scanForRepos(rootPath string) []RepoInfo {
	var repos []RepoInfo

	_ = filepath.Walk(rootPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil
		}

		if info.IsDir() && strings.HasPrefix(info.Name(), ".") && info.Name() != ".git" {
			return filepath.SkipDir
		}

		if info.IsDir() && info.Name() == ".git" {
			repoPath := filepath.Dir(path)
			repoInfo := analyzeRepo(repoPath)
			if repoInfo != nil {
				repos = append(repos, *repoInfo)
			}
			return filepath.SkipDir
		}

		return nil
	})

	return repos
}

func analyzeRepo(repoPath string) *RepoInfo {
	gitConfigPath := filepath.Join(repoPath, ".git", "config")
	if _, err := os.Stat(gitConfigPath); os.IsNotExist(err) {
		return nil
	}

	remoteURL := parseGitConfig(gitConfigPath)
	if remoteURL == "" {
		return nil
	}

	repoType, owner, repo := parseGitURL(remoteURL)
	if owner == "" || repo == "" {
		return nil
	}

	return &RepoInfo{
		Path:      repoPath,
		Name:      filepath.Base(repoPath),
		RemoteURL: remoteURL,
		RepoType:  repoType,
		Owner:     owner,
		Repo:      repo,
	}
}

func parseGitConfig(configPath string) string {
	file, err := os.Open(configPath)
	if err != nil {
		return ""
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	inRemoteOrigin := false

	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())

		if line == `[remote "origin"]` {
			inRemoteOrigin = true
			continue
		}

		if inRemoteOrigin && strings.HasPrefix(line, "url = ") {
			url := strings.TrimPrefix(line, "url = ")
			url = strings.TrimSpace(url)
			return strings.TrimSuffix(url, ".git")
		}

		if inRemoteOrigin && strings.HasPrefix(line, "[") {
			inRemoteOrigin = false
		}
	}

	return ""
}

func parseGitURL(url string) (string, string, string) {
	sshRegex := regexp.MustCompile(`^git@([^:]+):([^/]+)/(.+)$`)
	if matches := sshRegex.FindStringSubmatch(url); len(matches) == 4 {
		return getRepoType(matches[1]), matches[2], matches[3]
	}

	httpsRegex := regexp.MustCompile(`^https?://([^/]+)/([^/]+)/([^/]+?)(?:\.git)?$`)
	if matches := httpsRegex.FindStringSubmatch(url); len(matches) == 4 {
		return getRepoType(matches[1]), matches[2], matches[3]
	}

	return "other", "", ""
}

func getRepoType(host string) string {
	switch {
	case strings.Contains(host, "github.com"):
		return "github"
	case strings.Contains(host, "gitlab.com"):
		return "gitlab"
	case strings.Contains(host, "bitbucket.org"):
		return "bitbucket"
	default:
		return "other"
	}
}

func fetchRepoInfo(repo *RepoInfo) {
	switch repo.RepoType {
	case "github":
		fetchGitHubInfo(repo)
	case "gitlab":
		fetchGitLabInfo(repo)
	}
}

func fetchGitHubInfo(repo *RepoInfo) {
	url := fmt.Sprintf("https://api.github.com/repos/%s/%s", repo.Owner, repo.Repo)

	client := &http.Client{Timeout: 5 * time.Second}
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return
	}

	if token := os.Getenv("GITHUB_TOKEN"); token != "" {
		req.Header.Set("Authorization", "token "+token)
	}
	req.Header.Set("Accept", "application/vnd.github.v3+json")

	resp, err := client.Do(req)
	if err != nil {
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return
	}

	var githubResp gitHubAPIResponse
	if err := json.NewDecoder(resp.Body).Decode(&githubResp); err != nil {
		return
	}

	repo.Description = githubResp.Description
	repo.Stars = githubResp.Stargazers
	repo.Forks = githubResp.Forks
	repo.Language = githubResp.Language
	repo.UpdatedAt = githubResp.UpdatedAt
}

func fetchGitLabInfo(repo *RepoInfo) {
	projectPath := fmt.Sprintf("%s%%2F%s", repo.Owner, repo.Repo)
	url := fmt.Sprintf("https://gitlab.com/api/v4/projects/%s", projectPath)

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Get(url)
	if err != nil {
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return
	}

	var gitlabResp gitLabAPIResponse
	if err := json.NewDecoder(resp.Body).Decode(&gitlabResp); err != nil {
		return
	}

	repo.Description = gitlabResp.Description
	repo.Stars = gitlabResp.StarCount
	repo.Forks = gitlabResp.ForksCount
}
