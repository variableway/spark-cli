package gitlab

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"os/exec"
	"strings"
)

type Project struct {
	Name              string `json:"name"`
	Path              string `json:"path"`
	PathWithNamespace string `json:"path_with_namespace"`
	WebURL            string `json:"web_url"`
	SSHURL            string `json:"ssh_url_to_repo"`
	HTTPURL           string `json:"http_url_to_repo"`
	DefaultBranch     string `json:"default_branch"`
	Description       string `json:"description"`
	StarCount         int    `json:"star_count"`
	ForkedFrom        any    `json:"forked_from_project"`
}

func IsGitLabURL(input string) bool {
	input = strings.TrimSpace(input)
	input = strings.TrimSuffix(input, "/")

	if strings.Contains(input, "github.com/") {
		return false
	}

	if strings.HasPrefix(input, "http://") || strings.HasPrefix(input, "https://") {
		return true
	}

	return false
}

func ParseGitLabURL(input string) (baseURL, groupPath string, err error) {
	input = strings.TrimSpace(input)
	input = strings.TrimSuffix(input, "/")

	if !strings.HasPrefix(input, "http://") && !strings.HasPrefix(input, "https://") {
		return "", "", fmt.Errorf("invalid URL: %s", input)
	}

	u, err := url.Parse(input)
	if err != nil {
		return "", "", fmt.Errorf("failed to parse URL: %w", err)
	}

	baseURL = fmt.Sprintf("%s://%s", u.Scheme, u.Host)

	path := strings.TrimPrefix(u.Path, "/")
	path = strings.TrimSuffix(path, "/")

	if path == "" {
		return "", "", fmt.Errorf("no group path found in URL: %s", input)
	}

	return baseURL, path, nil
}

func GetReposForAccount(baseURL, accountName, token string) ([]Project, string, error) {
	if projects, err := glabGetGroupProjects(baseURL, accountName); err == nil {
		return projects, "group", nil
	}

	if projects, err := glabGetUserProjects(baseURL, accountName); err == nil {
		return projects, "user", nil
	}

	accountType, resolvedPath, err := detectAccountType(baseURL, accountName, token)
	if err != nil {
		return nil, "", err
	}

	var projects []Project
	switch accountType {
	case "group":
		projects, err = apiGetGroupProjects(baseURL, resolvedPath, token)
	case "user":
		projects, err = apiGetUserProjects(baseURL, resolvedPath, token)
	}

	if err != nil {
		return nil, "", err
	}

	return projects, accountType, nil
}

func detectAccountType(baseURL, name, token string) (string, string, error) {
	apiURL := fmt.Sprintf("%s/api/v4/groups/%s", baseURL, name)
	if code := apiCheck(apiURL, token); code == http.StatusOK {
		return "group", name, nil
	}

	apiURL = fmt.Sprintf("%s/api/v4/users/%s", baseURL, name)
	if code := apiCheck(apiURL, token); code == http.StatusOK {
		return "user", name, nil
	}

	parts := strings.Split(name, "/")
	for i := len(parts) - 1; i > 0; i-- {
		parentPath := strings.Join(parts[:i], "/")
		apiURL = fmt.Sprintf("%s/api/v4/groups/%s", baseURL, parentPath)
		if code := apiCheck(apiURL, token); code == http.StatusOK {
			return "group", parentPath, nil
		}
	}

	return "", "", fmt.Errorf("account '%s' not found on %s\n\nHint: for private GitLab instances, provide a token:\n  spark git batch-clone <url> --token <your-token>\n  or set GITLAB_TOKEN env var\n  or install & auth glab CLI: https://gitlab.com/gitlab-org/cli", name, baseURL)
}

func apiCheck(apiURL, token string) int {
	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		return 0
	}
	if token != "" {
		req.Header.Set("PRIVATE-TOKEN", token)
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return 0
	}
	resp.Body.Close()
	return resp.StatusCode
}

func apiGetGroupProjects(baseURL, groupPath, token string) ([]Project, error) {
	var all []Project
	page := 1
	for {
		apiURL := fmt.Sprintf("%s/api/v4/groups/%s/projects?per_page=100&page=%d&include_subgroups=true",
			baseURL, groupPath, page)
		projects, err := apiFetchProjects(apiURL, token)
		if err != nil {
			return nil, err
		}
		all = append(all, projects...)
		if len(projects) < 100 {
			break
		}
		page++
	}
	return all, nil
}

func apiGetUserProjects(baseURL, username, token string) ([]Project, error) {
	var all []Project
	page := 1
	for {
		apiURL := fmt.Sprintf("%s/api/v4/users/%s/projects?per_page=100&page=%d",
			baseURL, username, page)
		projects, err := apiFetchProjects(apiURL, token)
		if err != nil {
			return nil, err
		}
		all = append(all, projects...)
		if len(projects) < 100 {
			break
		}
		page++
	}
	return all, nil
}

func apiFetchProjects(apiURL, token string) ([]Project, error) {
	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	if token != "" {
		req.Header.Set("PRIVATE-TOKEN", token)
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch projects: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNotFound {
		return nil, fmt.Errorf("resource not found: %s", apiURL)
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("failed to fetch projects: HTTP %d", resp.StatusCode)
	}

	var projects []Project
	if err := json.NewDecoder(resp.Body).Decode(&projects); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}
	return projects, nil
}

func glabAvailable() bool {
	_, err := exec.LookPath("glab")
	return err == nil
}

func glabGetGroupProjects(baseURL, groupPath string) ([]Project, error) {
	if !glabAvailable() {
		return nil, fmt.Errorf("glab not available")
	}

	candidates := buildGroupCandidates(groupPath)

	for _, candidate := range candidates {
		projects, err := glabFetchGroupProjects(baseURL, candidate)
		if err == nil && len(projects) > 0 {
			return projects, nil
		}
	}

	return nil, fmt.Errorf("no projects found for '%s'", groupPath)
}

func glabFetchGroupProjects(baseURL, groupPath string) ([]Project, error) {
	var all []Project
	page := 1
	for {
		apiPath := fmt.Sprintf("/groups/%s/projects?per_page=100&page=%d&include_subgroups=true", groupPath, page)
		output, err := glabAPI(baseURL, apiPath)
		if err != nil {
			return nil, err
		}
		var projects []Project
		if err := json.Unmarshal(output, &projects); err != nil {
			return nil, fmt.Errorf("failed to parse glab response: %w", err)
		}
		all = append(all, projects...)
		if len(projects) < 100 {
			break
		}
		page++
	}
	return all, nil
}

func glabGetUserProjects(baseURL, username string) ([]Project, error) {
	if !glabAvailable() {
		return nil, fmt.Errorf("glab not available")
	}

	var all []Project
	page := 1
	for {
		apiPath := fmt.Sprintf("/users/%s/projects?per_page=100&page=%d", username, page)
		output, err := glabAPI(baseURL, apiPath)
		if err != nil {
			return nil, err
		}
		var projects []Project
		if err := json.Unmarshal(output, &projects); err != nil {
			return nil, fmt.Errorf("failed to parse glab response: %w", err)
		}
		all = append(all, projects...)
		if len(projects) < 100 {
			break
		}
		page++
	}
	return all, nil
}

func buildGroupCandidates(groupPath string) []string {
	parts := strings.Split(groupPath, "/")
	candidates := make([]string, 0, len(parts))
	for i := len(parts); i > 0; i-- {
		candidates = append(candidates, strings.Join(parts[:i], "/"))
	}
	return candidates
}

func glabAPI(baseURL, apiPath string) ([]byte, error) {
	args := []string{"api", "--hostname", extractHost(baseURL), apiPath}
	cmd := exec.Command("glab", args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("glab api failed: %s: %w", string(output), err)
	}
	return output, nil
}

func extractHost(baseURL string) string {
	u, err := url.Parse(baseURL)
	if err != nil {
		return baseURL
	}
	return u.Host
}
