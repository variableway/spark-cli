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
