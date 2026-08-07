package git

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
)

// InitAllSubmodules runs `git submodule update --init --recursive` to clone
// and checkout all registered submodules. When parallel > 1, submodules are
// initialized concurrently using goroutines.
func InitAllSubmodules(repoPath string, recursive bool, parallel int) error {
	if parallel <= 1 {
		return initSubmodulesSequential(repoPath, recursive)
	}
	return initSubmodulesParallel(repoPath, recursive, parallel)
}

func initSubmodulesSequential(repoPath string, recursive bool) error {
	args := []string{"submodule", "update", "--init"}
	if recursive {
		args = append(args, "--recursive")
	}

	cmd := exec.Command("git", args...)
	cmd.Dir = repoPath
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("git submodule update --init failed: %w", err)
	}
	return nil
}

func initSubmodulesParallel(repoPath string, recursive bool, parallel int) error {
	statuses, err := listSubmoduleStatus(repoPath)
	if err != nil {
		return fmt.Errorf("failed to list submodule status: %w", err)
	}

	if len(statuses) == 0 {
		fmt.Println("No submodules to initialize.")
		return nil
	}

	fmt.Printf("Initializing %d submodule(s) (parallel=%d)...\n", len(statuses), parallel)

	sem := make(chan struct{}, parallel)
	var wg sync.WaitGroup
	var mu sync.Mutex
	var firstErr error

	for _, st := range statuses {
		wg.Add(1)
		go func(s submoduleStatus) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			if err := initSingleSubmodule(repoPath, s.path); err != nil {
				mu.Lock()
				if firstErr == nil {
					firstErr = err
				}
				fmt.Fprintf(os.Stderr, "Error init %s: %v\n", s.path, err)
				mu.Unlock()
			}
		}(st)
	}

	wg.Wait()

	if recursive {
		fmt.Println("Initializing nested submodules...")
		args := []string{"submodule", "update", "--init", "--recursive"}
		cmd := exec.Command("git", args...)
		cmd.Dir = repoPath
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		cmd.Run() // best-effort for nested
	}

	return firstErr
}

func initSingleSubmodule(repoPath, name string) error {
	fmt.Printf("  Init %s ...", name)
	args := []string{"submodule", "update", "--init", name}
	cmd := exec.Command("git", args...)
	cmd.Dir = repoPath
	out, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Println(" FAILED")
		return fmt.Errorf("%s: %s", err, strings.TrimSpace(string(out)))
	}
	fmt.Println(" done")
	return nil
}

type submoduleStatus struct {
	path   string
	commit string
}

func listSubmoduleStatus(repoPath string) ([]submoduleStatus, error) {
	cmd := exec.Command("git", "submodule", "status")
	cmd.Dir = repoPath
	out, err := cmd.Output()
	if err != nil {
		return nil, err
	}

	var statuses []submoduleStatus
	for _, line := range strings.Split(strings.TrimSpace(string(out)), "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		uninitialized := strings.HasPrefix(line, "-")
		line = strings.TrimPrefix(line, "-")
		line = strings.TrimPrefix(line, "+")
		line = strings.TrimPrefix(line, " ")

		fields := strings.Fields(line)
		if len(fields) < 2 {
			continue
		}

		if uninitialized {
			statuses = append(statuses, submoduleStatus{
				path:   fields[1],
				commit: fields[0],
			})
		}
	}
	return statuses, nil
}

// EnsureSSHRemotes rewrites HTTPS remote URLs to SSH format for all submodules
// in the given repo. This helps when HTTPS connections to GitHub are unreliable.
func EnsureSSHRemotes(repoPath string) error {
	rewriteRepoRemote(repoPath)
	return rewriteGitModulesURLs(repoPath)
}

func rewriteRepoRemote(repoPath string) {
	cmd := exec.Command("git", "remote", "get-url", "origin")
	cmd.Dir = repoPath
	out, err := cmd.Output()
	if err != nil {
		return
	}
	url := strings.TrimSpace(string(out))
	sshURL := httpsToSSH(url)
	if sshURL == url {
		return
	}
	fmt.Printf("Rewriting parent remote: %s -> %s\n", url, sshURL)
	exec.Command("git", "-C", repoPath, "remote", "set-url", "origin", sshURL).Run()
}

func rewriteGitModulesURLs(repoPath string) error {
	gitmodules := filepath.Join(repoPath, ".gitmodules")
	data, err := os.ReadFile(gitmodules)
	if err != nil {
		return nil
	}

	content := string(data)
	lines := strings.Split(content, "\n")
	changed := false
	for i, line := range lines {
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, "url = https://github.com/") {
			urlPart := strings.TrimPrefix(trimmed, "url = ")
			sshURL := httpsToSSH(urlPart)
			if sshURL != urlPart {
				indent := line[:len(line)-len(trimmed)]
				lines[i] = indent + "url = " + sshURL
				changed = true
			}
		}
	}

	if changed {
		fmt.Printf("Rewriting .gitmodules: HTTPS -> SSH\n")
		return os.WriteFile(gitmodules, []byte(strings.Join(lines, "\n")), 0644)
	}
	return nil
}

func httpsToSSH(url string) string {
	if strings.HasPrefix(url, "https://") {
		withoutScheme := strings.TrimPrefix(url, "https://")
		if idx := strings.Index(withoutScheme, "/"); idx != -1 {
			host := withoutScheme[:idx]
			path := withoutScheme[idx+1:]
			return "git@" + host + ":" + path
		}
	}
	return url
}

// SubmoduleInfo represents the status of a single submodule.
type SubmoduleInfo struct {
	Path         string
	Commit       string
	Initialized  bool
	Branch       string
}

// AddExistingRepoAsSubmodule registers an already-present local git repository
// (located at repoPath/name) as a submodule of repoPath without re-cloning it.
// It writes the .gitmodules entry, stages the directory as a gitlink pointing
// at the child's current HEAD, and registers the URL in .git/config. This is
// the fallback used when `git submodule add` cannot run because the target
// directory already exists.
func AddExistingRepoAsSubmodule(repoPath, name, url string) error {
	if err := ensureGitmodulesEntry(repoPath, name, url); err != nil {
		return fmt.Errorf("failed to update .gitmodules: %w", err)
	}

	// Resolve the commit the submodule should point at.
	revCmd := exec.Command("git", "rev-parse", "HEAD")
	revCmd.Dir = filepath.Join(repoPath, name)
	revOut, err := revCmd.Output()
	if err != nil {
		return fmt.Errorf("failed to resolve HEAD of %s: %w", name, err)
	}
	commit := strings.TrimSpace(string(revOut))

	// Drop any regular-file tracking of name so the path can become a gitlink.
	// --ignore-unmatch makes this a no-op when nothing is tracked.
	rm := exec.Command("git", "rm", "--cached", "-r", "--ignore-unmatch", "--", name)
	rm.Dir = repoPath
	rm.Run() // best-effort

	// Stage the directory as a gitlink at the child's HEAD. update-index is the
	// right primitive here: it records the pointer directly, without re-cloning
	// and without the "adding embedded git repository" warning `git add` emits.
	stage := exec.Command("git", "update-index", "--add", "--replace",
		"--cacheinfo", fmt.Sprintf("160000,%s,%s", commit, name))
	stage.Dir = repoPath
	stage.Stdout = os.Stdout
	stage.Stderr = os.Stderr
	if err := stage.Run(); err != nil {
		return fmt.Errorf("failed to stage submodule %s: %w", name, err)
	}

	// Copy the URL from .gitmodules into .git/config. Needs the gitlink staged.
	init := exec.Command("git", "submodule", "init", "--", name)
	init.Dir = repoPath
	init.Stdout = os.Stdout
	init.Stderr = os.Stderr
	init.Run() // best-effort; harmless if already registered

	gmAdd := exec.Command("git", "add", "--", ".gitmodules")
	gmAdd.Dir = repoPath
	gmAdd.Stdout = os.Stdout
	gmAdd.Stderr = os.Stderr
	return gmAdd.Run()
}

// ensureGitmodulesEntry appends a [submodule "<name>"] block (path + url) to
// .gitmodules, creating the file if needed. It is a no-op when an entry for
// name already exists.
func ensureGitmodulesEntry(repoPath, name, url string) error {
	gitmodules := filepath.Join(repoPath, ".gitmodules")
	data, _ := os.ReadFile(gitmodules)
	content := string(data)
	if strings.Contains(content, fmt.Sprintf("submodule %q", name)) {
		return nil
	}

	var sb strings.Builder
	if content != "" && !strings.HasSuffix(content, "\n") {
		sb.WriteString("\n")
	}
	sb.WriteString(fmt.Sprintf("[submodule %q]\n", name))
	sb.WriteString(fmt.Sprintf("\tpath = %s\n", name))
	sb.WriteString(fmt.Sprintf("\turl = %s\n", url))

	f, err := os.OpenFile(gitmodules, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	defer f.Close()
	_, err = f.WriteString(sb.String())
	return err
}

// GetSubmoduleStatus returns the status of all submodules in a repo.
func GetSubmoduleStatus(repoPath string) ([]SubmoduleInfo, error) {
	cmd := exec.Command("git", "submodule", "status")
	cmd.Dir = repoPath
	out, err := cmd.Output()
	if err != nil {
		return nil, err
	}

	var statuses []SubmoduleInfo
	for _, line := range strings.Split(strings.TrimSpace(string(out)), "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		initialized := true
		if strings.HasPrefix(line, "-") {
			initialized = false
		}
		line = strings.TrimPrefix(line, "-")
		line = strings.TrimPrefix(line, "+")
		line = strings.TrimPrefix(line, " ")

		fields := strings.Fields(line)
		if len(fields) < 2 {
			continue
		}

		st := SubmoduleInfo{
			Commit:      fields[0],
			Path:        fields[1],
			Initialized: initialized,
		}
		if len(fields) > 2 {
			branch := strings.Trim(fields[2], "()")
			st.Branch = branch
		}
		statuses = append(statuses, st)
	}
	return statuses, nil
}
