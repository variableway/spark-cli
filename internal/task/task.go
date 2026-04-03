package task

import (
	"fmt"
	"io"
	"spark/internal/tui"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

type Manager struct {
	TaskDir     string
	GitHubOwner string
	WorkDir     string
	UI          *tui.UI
}

func NewManager(taskDir, owner, workDir string, useTUI bool) *Manager {
	if workDir == "" {
		workDir = "."
	}
	return &Manager{
		TaskDir:     taskDir,
		GitHubOwner: owner,
		WorkDir:     workDir,
		UI:          tui.New(useTUI),
	}
}

func (m *Manager) Dispatch(taskName string, destPath string) error {
	srcPath := filepath.Join(m.TaskDir, taskName)
	if _, err := os.Stat(srcPath); os.IsNotExist(err) {
		return fmt.Errorf("task not found: %s", srcPath)
	}

	if destPath == "" {
		destPath = filepath.Join(m.WorkDir, taskName)
	}

	if _, err := os.Stat(destPath); os.IsNotExist(err) {
		if err := os.MkdirAll(destPath, 0755); err != nil {
			return fmt.Errorf("failed to create destination directory: %w", err)
		}
	}

	err := m.UI.Spinner("Copying markdown files", func() error {
		return CopyMarkdownFiles(srcPath, destPath)
	})
	if err != nil {
		return fmt.Errorf("failed to copy markdown files: %w", err)
	}
	m.UI.Printf("  From: %s\n", srcPath)
	m.UI.Printf("  To:   %s\n", destPath)

	err = m.UI.Spinner("Initializing git repository", func() error {
		return initGitRepo(destPath, m.UI)
	})
	if err != nil {
		return fmt.Errorf("failed to initialize git: %w", err)
	}

	repoFullName := fmt.Sprintf("%s/%s", m.GitHubOwner, taskName)
	err = m.UI.Spinner(fmt.Sprintf("Creating GitHub repository %s", repoFullName), func() error {
		return createGitHubRepo(destPath, m.GitHubOwner, taskName, m.UI)
	})
	if err != nil {
		return fmt.Errorf("failed to create GitHub repository: %w", err)
	}

	m.UI.Success("Task dispatched successfully!")
	m.UI.Printf("  Location: %s\n", destPath)
	m.UI.Printf("  GitHub:   https://github.com/%s/%s\n", m.GitHubOwner, taskName)

	return nil
}

func (m *Manager) SyncBack(taskName string, workPath string) error {
	if workPath == "" {
		workPath = filepath.Join(m.WorkDir, taskName)
	}

	destPath := filepath.Join(m.TaskDir, taskName)

	if _, err := os.Stat(workPath); os.IsNotExist(err) {
		return fmt.Errorf("task working directory not found: %s", workPath)
	}

	err := m.UI.Spinner("Syncing markdown files", func() error {
		return CopyMarkdownFiles(workPath, destPath)
	})
	if err != nil {
		return fmt.Errorf("failed to sync markdown files: %w", err)
	}
	m.UI.Printf("  From: %s\n", workPath)
	m.UI.Printf("  To:   %s\n", destPath)

	m.UI.Success("Task synced successfully!")
	m.UI.Printf("  Location: %s\n", destPath)

	return nil
}

func (m *Manager) ListTasks() ([]string, error) {
	entries, err := os.ReadDir(m.TaskDir)
	if err != nil {
		return nil, fmt.Errorf("failed to read task directory: %w", err)
	}

	var tasks []string
	for _, entry := range entries {
		if entry.IsDir() {
			tasks = append(tasks, entry.Name())
		}
	}
	return tasks, nil
}

func copyDirectory(src, dst string) error {
	return filepath.Walk(src, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		relPath, err := filepath.Rel(src, path)
		if err != nil {
			return err
		}
		dstPath := filepath.Join(dst, relPath)

		if info.IsDir() {
			return os.MkdirAll(dstPath, info.Mode())
		}

		return copyFile(path, dstPath)
	})
}

func CopyMarkdownFiles(src, dst string) error {
	return filepath.Walk(src, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		if info.IsDir() {
			return nil
		}

		if !strings.HasSuffix(strings.ToLower(info.Name()), ".md") {
			return nil
		}

		relPath, err := filepath.Rel(src, path)
		if err != nil {
			return err
		}
		dstPath := filepath.Join(dst, relPath)

		dstDir := filepath.Dir(dstPath)
		if err := os.MkdirAll(dstDir, 0755); err != nil {
			return err
		}

		return copyFile(path, dstPath)
	})
}

func copyFile(src, dst string) error {
	srcFile, err := os.Open(src)
	if err != nil {
		return err
	}
	defer srcFile.Close()

	dstFile, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer dstFile.Close()

	_, err = io.Copy(dstFile, srcFile)
	return err
}

func initGitRepo(path string, ui *tui.UI) error {
	cmd := exec.Command("git", "init")
	cmd.Dir = path
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return err
	}

	cmd = exec.Command("git", "add", ".")
	cmd.Dir = path
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return err
	}

	cmd = exec.Command("git", "commit", "-m", "Initial commit")
	cmd.Dir = path
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

func createGitHubRepo(path, owner, name string, ui *tui.UI) error {
	cmd := exec.Command("gh", "repo", "create", fmt.Sprintf("%s/%s", owner, name),
		"--public",
		"--source=.",
		"--push")
	cmd.Dir = path
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}
