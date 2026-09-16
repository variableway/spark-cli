package gitlab

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"os/exec"
	"strings"
)

const (
	TokenSourceFlag   = "--token flag"
	TokenSourceConfig = "gitlab.token in ~/.spark.yaml"
	TokenSourceEnv    = "GITLAB_TOKEN environment variable"
	TokenSourceEnvAlt = "GITLAB_PRIVATE_TOKEN environment variable"
)

// tokenOrigin labels a credential with the place it was read from
func tokenOrigin(source string) string {
	if source == "" {
		return "The credentials sent to the API"
	}
	return "The token from " + source
}

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

	host, _, found := strings.Cut(input, "/")
	return found && strings.Contains(host, ".")
}

func ParseGitLabURL(input string) (baseURL, groupPath string, err error) {
	input = strings.TrimSpace(input)
	input = strings.TrimSuffix(input, "/")

	if !strings.Contains(input, "://") {
		input = "https://" + input
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

func escapePath(path string) string {
	return url.PathEscape(path)
}

// ProjectRelativePath keeps the subgroup structure below namespace, so that
// same-named projects in different subgroups never collide.
func ProjectRelativePath(project Project, namespace string) string {
	namespace = strings.Trim(strings.TrimSpace(namespace), "/")
	pathWithNamespace := strings.Trim(strings.TrimSpace(project.PathWithNamespace), "/")

	if namespace != "" && strings.HasPrefix(pathWithNamespace, namespace+"/") {
		if relative := strings.TrimPrefix(pathWithNamespace, namespace+"/"); relative != "" {
			return relative
		}
	}

	if project.Path != "" {
		return project.Path
	}
	return pathWithNamespace
}

func GetReposForAccount(baseURL, accountName, token, tokenSource string) ([]Project, string, error) {
	if token != "" {
		if projects, accountType, err := apiGetProjectsForAccount(baseURL, accountName, token, tokenSource); err == nil {
			return projects, accountType, nil
		}
	}

	if projects, err := glabGetGroupProjects(baseURL, accountName); err == nil {
		return projects, "group", nil
	}

	if projects, err := glabGetUserProjects(baseURL, accountName); err == nil {
		return projects, "user", nil
	}

	return apiGetProjectsForAccount(baseURL, accountName, token, tokenSource)
}

func apiGetProjectsForAccount(baseURL, accountName, token, tokenSource string) ([]Project, string, error) {
	accountType, resolvedPath, err := detectAccountType(baseURL, accountName, token, tokenSource)
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

func detectAccountType(baseURL, name, token, tokenSource string) (string, string, error) {
	unauthorized := false
	check := func(apiPath string) int {
		code := apiCheck(fmt.Sprintf("%s/api/v4/%s", baseURL, apiPath), token)
		if code == http.StatusUnauthorized || code == http.StatusForbidden {
			unauthorized = true
		}
		return code
	}

	if code := check("groups/" + escapePath(name)); code == http.StatusOK {
		return "group", name, nil
	}

	if code := check("users/" + escapePath(name)); code == http.StatusOK {
		return "user", name, nil
	}

	parts := strings.Split(name, "/")
	for i := len(parts) - 1; i > 0; i-- {
		parentPath := strings.Join(parts[:i], "/")
		if code := check("groups/" + escapePath(parentPath)); code == http.StatusOK {
			return "group", parentPath, nil
		}
	}

	if unauthorized {
		return "", "", fmt.Errorf("authentication failed for '%s' on %s\n\n%s was rejected by the instance (missing, expired or lacking access to this resource):\n  spark git batch-clone <url> --token <your-token>\n  or set GITLAB_TOKEN env var\n  or set gitlab.token in ~/.spark.yaml\n  or refresh your glab credentials: glab auth login --hostname %s",
			name, baseURL, tokenOrigin(tokenSource), ExtractHost(baseURL))
	}

	if token == "" {
		return "", "", fmt.Errorf("account '%s' not found on %s without credentials\n\nSelf-hosted instances and private groups return 404 instead of 401 when unauthenticated,\nso a missing token is the most likely cause. Configure one with:\n  spark git batch-clone <url> --token <your-token>\n  or set GITLAB_TOKEN env var\n  or set gitlab.token in ~/.spark.yaml\n  or authenticate glab: glab auth login --hostname %s",
			name, baseURL, ExtractHost(baseURL))
	}

	return "", "", fmt.Errorf("account '%s' not found on %s\n\n%s was sent but the group path could not be resolved. Check that:\n  - the group path is correct (nested groups are URL-encoded automatically)\n  - the token has the read_api scope and access to this group",
		name, baseURL, tokenOrigin(tokenSource))
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
			baseURL, escapePath(groupPath), page)
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
			baseURL, escapePath(username), page)
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
		apiPath := fmt.Sprintf("/groups/%s/projects?per_page=100&page=%d&include_subgroups=true", escapePath(groupPath), page)
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
		apiPath := fmt.Sprintf("/users/%s/projects?per_page=100&page=%d", escapePath(username), page)
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
	args := []string{"api", "--hostname", ExtractHost(baseURL), apiPath}
	cmd := exec.Command("glab", args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("glab api failed: %s: %w", string(output), err)
	}
	return output, nil
}

// ExtractHost normalizes a GitLab instance reference (URL, bare host or
// host:port) into a lowercase host for comparison.
func ExtractHost(value string) string {
	value = strings.TrimSpace(value)
	value = strings.TrimSuffix(value, "/")

	if !strings.Contains(value, "://") {
		if i := strings.Index(value, "/"); i >= 0 {
			value = value[:i]
		}
		return strings.ToLower(value)
	}

	u, err := url.Parse(value)
	if err != nil || u.Host == "" {
		return strings.ToLower(value)
	}
	return strings.ToLower(u.Host)
}
