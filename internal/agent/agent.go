package agent

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
)

type AgentType string

const (
	AgentClaudeCode AgentType = "claude-code"
	AgentCodex      AgentType = "codex"
	AgentKimi       AgentType = "kimi"
	AgentGLM        AgentType = "glm"
)

type AgentConfig struct {
	Name        AgentType
	DisplayName string
	ConfigFiles []string
}

var AgentConfigs = map[AgentType]AgentConfig{
	AgentClaudeCode: {
		Name:        AgentClaudeCode,
		DisplayName: "Claude Code",
		ConfigFiles: []string{
			".claude.json",
			".claude/settings.json",
			".claude/settings.local.json",
		},
	},
	AgentCodex: {
		Name:        AgentCodex,
		DisplayName: "OpenAI Codex",
		ConfigFiles: []string{
			".codex/config.toml",
		},
	},
	AgentKimi: {
		Name:        AgentKimi,
		DisplayName: "Kimi CLI",
		ConfigFiles: []string{
			".kimi/config.toml",
		},
	},
	AgentGLM: {
		Name:        AgentGLM,
		DisplayName: "GLM (Zhipu AI)",
		ConfigFiles: []string{
			".claude.json",
			".claude/settings.json",
		},
	},
}

type Manager struct {
	homeDir string
	editor  string
}

func NewManager() *Manager {
	homeDir, _ := os.UserHomeDir()
	editor := os.Getenv("EDITOR")
	if editor == "" {
		if runtime.GOOS == "windows" {
			editor = "notepad"
		} else {
			editor = "vim"
		}
	}
	return &Manager{
		homeDir: homeDir,
		editor:  editor,
	}
}

func (m *Manager) GetAgentConfigPath(agent AgentType) ([]string, error) {
	config, ok := AgentConfigs[agent]
	if !ok {
		return nil, fmt.Errorf("unknown agent: %s", agent)
	}

	var paths []string
	for _, file := range config.ConfigFiles {
		paths = append(paths, filepath.Join(m.homeDir, file))
	}
	return paths, nil
}

func (m *Manager) ListAgents() []AgentConfig {
	var result []AgentConfig
	for _, config := range AgentConfigs {
		result = append(result, config)
	}
	return result
}

func (m *Manager) ViewConfig(agent AgentType) (map[string]string, error) {
	paths, err := m.GetAgentConfigPath(agent)
	if err != nil {
		return nil, err
	}

	results := make(map[string]string)
	for _, path := range paths {
		content, err := os.ReadFile(path)
		if err != nil {
			if os.IsNotExist(err) {
				continue
			}
			return nil, fmt.Errorf("failed to read %s: %w", path, err)
		}
		results[path] = string(content)
	}

	if len(results) == 0 {
		return nil, fmt.Errorf("no config files found for %s", agent)
	}

	return results, nil
}

func (m *Manager) EditConfig(agent AgentType, configFileIndex int) error {
	paths, err := m.GetAgentConfigPath(agent)
	if err != nil {
		return err
	}

	if configFileIndex < 0 || configFileIndex >= len(paths) {
		return fmt.Errorf("invalid config file index: %d (available: 0-%d)", configFileIndex, len(paths)-1)
	}

	path := paths[configFileIndex]

	dir := filepath.Dir(path)
	if _, err := os.Stat(dir); os.IsNotExist(err) {
		if err := os.MkdirAll(dir, 0755); err != nil {
			return fmt.Errorf("failed to create directory: %w", err)
		}
	}

	cmd := exec.Command(m.editor, path)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

func (m *Manager) ResetConfig(agent AgentType) error {
	paths, err := m.GetAgentConfigPath(agent)
	if err != nil {
		return err
	}

	for _, path := range paths {
		if _, err := os.Stat(path); err == nil {
			backupPath := path + ".bak"
			if err := os.Rename(path, backupPath); err != nil {
				return fmt.Errorf("failed to backup %s: %w", path, err)
			}
		}
	}
	return nil
}

func (m *Manager) ConfigExists(agent AgentType) map[string]bool {
	paths, err := m.GetAgentConfigPath(agent)
	if err != nil {
		return nil
	}

	results := make(map[string]bool)
	for _, path := range paths {
		_, err := os.Stat(path)
		results[path] = err == nil
	}
	return results
}

func (m *Manager) GetAgentInfo(agent AgentType) (*AgentConfig, error) {
	config, ok := AgentConfigs[agent]
	if !ok {
		return nil, fmt.Errorf("unknown agent: %s", agent)
	}
	return &config, nil
}
