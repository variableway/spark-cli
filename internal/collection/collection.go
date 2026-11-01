package collection

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"spark/internal/github"
	"spark/internal/registry"
)

const (
	CategoryBase      = "base"
	CategoryApp       = "app"
	CategoryReference = "reference"

	StatusMaintained   = "maintained"
	StatusArchived     = "archived"
	StatusExperimental = "experimental"

	VisibilityPublic  = "public"
	VisibilityPrivate = "private"
)

var Categories = []string{CategoryBase, CategoryApp, CategoryReference}

type Entry struct {
	Name        string `json:"name"`
	Title       string `json:"title,omitempty"`
	Repo        string `json:"repo"`
	URL         string `json:"url,omitempty"`
	LocalPath   string `json:"local_path,omitempty"`
	Category    string `json:"category"`
	Status      string `json:"status"`
	Visibility  string `json:"visibility"`
	Language    string `json:"language,omitempty"`
	Description string `json:"description,omitempty"`
}

type Registry struct {
	Schema      string  `json:"$schema,omitempty"`
	Version     int     `json:"version"`
	UpdatedAt   string  `json:"updated_at"`
	Collections []Entry `json:"collections"`
}

var githubRepoRe = regexp.MustCompile(`^(?:https://github\.com/|git@github\.com:)([^/]+)/([^/]+?)(?:\.git)?$`)

// ParseGitHubRepo extracts owner/repo from a GitHub remote URL.
func ParseGitHubRepo(remoteURL string) (owner, repo string, ok bool) {
	m := githubRepoRe.FindStringSubmatch(strings.TrimSpace(remoteURL))
	if m == nil {
		return "", "", false
	}
	return m[1], m[2], true
}

// FromGitHubRepo builds an Entry from a GitHub API repository response.
func FromGitHubRepo(repo *github.Repository, localPath string) Entry {
	owner := repo.Owner.Login
	name := repo.Name

	visibility := VisibilityPublic
	if repo.Private {
		visibility = VisibilityPrivate
	}

	url := repo.Homepage
	if url == "" {
		url = repo.HTMLURL
	}

	title := repo.Description
	if title == "" {
		title = humanize(name)
	}

	return Entry{
		Name:        name,
		Title:       title,
		Repo:        owner + "/" + name,
		URL:         url,
		LocalPath:   filepath.ToSlash(localPath),
		Category:    CategoryApp,
		Status:      StatusMaintained,
		Visibility:  visibility,
		Language:    repo.Language,
		Description: repo.Description,
	}
}

// FromRemoteURL builds an Entry from a git remote URL without API calls.
func FromRemoteURL(remoteURL, localPath string) (Entry, bool) {
	owner, name, ok := ParseGitHubRepo(remoteURL)
	if !ok {
		return Entry{}, false
	}
	return Entry{
		Name:       name,
		Title:      humanize(name),
		Repo:       owner + "/" + name,
		URL:        fmt.Sprintf("https://github.com/%s/%s", owner, name),
		LocalPath:  filepath.ToSlash(localPath),
		Category:   CategoryApp,
		Status:     StatusMaintained,
		Visibility: VisibilityPublic,
	}, true
}

// Scan discovers git repositories under root and converts them to registry entries.
// GitHub repos are enriched via the GitHub API unless skipAPI is set.
// maxDepth limits how deep to look for repos (1 = top-level only, 0 = unlimited).
func Scan(root string, skipAPI bool, maxDepth int) ([]Entry, error) {
	projects, err := registry.Scan(root)
	if err != nil {
		return nil, err
	}

	var entries []Entry
	for _, p := range projects {
		if maxDepth > 0 && strings.Count(filepath.ToSlash(p.Path), "/") >= maxDepth {
			continue
		}

		owner, repoName, ok := ParseGitHubRepo(p.Repo)
		if !ok {
			if e, ok := FromRemoteURL(p.Repo, p.Path); ok {
				entries = append(entries, e)
			}
			continue
		}

		if skipAPI {
			if e, ok := FromRemoteURL(p.Repo, p.Path); ok {
				entries = append(entries, e)
			}
			continue
		}

		repo, err := github.GetRepo(owner, repoName)
		if err != nil {
			if e, ok := FromRemoteURL(p.Repo, p.Path); ok {
				entries = append(entries, e)
			}
			continue
		}
		entries = append(entries, FromGitHubRepo(repo, p.Path))
	}
	return entries, nil
}

// Merge keeps curated fields (title, category, status, url, description) from
// existing entries, refreshes auto-detected fields, appends new discoveries,
// and preserves existing entries that were not found during the scan.
func Merge(existing, discovered []Entry) []Entry {
	byName := make(map[string]Entry, len(discovered))
	byRepo := make(map[string]Entry, len(discovered))
	for _, d := range discovered {
		byName[d.Name] = d
		byRepo[d.Repo] = d
	}

	final := make([]Entry, 0, len(discovered))
	matched := make(map[string]bool, len(discovered))

	for _, old := range existing {
		d, ok := byName[old.Name]
		if !ok {
			d, ok = byRepo[old.Repo]
		}
		if !ok {
			final = append(final, old)
			continue
		}
		merged := d
		if old.Title != "" {
			merged.Title = old.Title
		}
		if old.Category != "" {
			merged.Category = old.Category
		}
		if old.Status != "" {
			merged.Status = old.Status
		}
		if old.URL != "" {
			merged.URL = old.URL
		}
		if old.Description != "" {
			merged.Description = old.Description
		}
		final = append(final, merged)
		matched[d.Name] = true
	}

	for _, d := range discovered {
		if matched[d.Name] {
			continue
		}
		final = append(final, d)
	}
	return final
}

// Read loads an existing Registry from a JSON file. Missing files yield an empty registry.
func Read(path string) (*Registry, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return &Registry{Version: 1}, nil
		}
		return nil, fmt.Errorf("read registry: %w", err)
	}
	var reg Registry
	if err := json.Unmarshal(data, &reg); err != nil {
		return nil, fmt.Errorf("parse registry %s: %w", path, err)
	}
	return &reg, nil
}

// Write serializes the registry as pretty JSON. Empty path prints to stdout.
func Write(path string, reg *Registry) error {
	if reg.Schema == "" {
		reg.Schema = "./schema.json"
	}
	if reg.Version == 0 {
		reg.Version = 1
	}
	reg.UpdatedAt = time.Now().Format("2006-01-02")

	out, err := json.MarshalIndent(reg, "", "  ")
	if err != nil {
		return fmt.Errorf("encode registry: %w", err)
	}
	if path == "" {
		fmt.Println(string(out))
		return nil
	}
	return os.WriteFile(path, append(out, '\n'), 0644)
}

func humanize(name string) string {
	parts := strings.FieldsFunc(name, func(r rune) bool {
		return r == '-' || r == '_' || r == '.'
	})
	for i, p := range parts {
		if len(p) > 0 {
			parts[i] = strings.ToUpper(p[:1]) + p[1:]
		}
	}
	return strings.Join(parts, " ")
}
