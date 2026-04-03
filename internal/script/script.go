package script

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/spf13/viper"
)

// Script represents a script configuration
type Script struct {
	Name    string `mapstructure:"name" yaml:"name"`
	Content string `mapstructure:"content" yaml:"content"`
	Path    string `mapstructure:"path" yaml:"path"`
}

// ScriptManager manages script operations
type ScriptManager struct {
	scriptsDir string
}

// NewScriptManager creates a new ScriptManager
func NewScriptManager(scriptsDir string) *ScriptManager {
	if scriptsDir == "" {
		scriptsDir = "scripts"
	}
	return &ScriptManager{
		scriptsDir: scriptsDir,
	}
}

// GetScriptsDir returns the scripts directory
func (sm *ScriptManager) GetScriptsDir() string {
	return sm.scriptsDir
}

// LoadScriptsFromConfig loads scripts from viper config
func (sm *ScriptManager) LoadScriptsFromConfig() ([]Script, error) {
	var scripts []Script

	// Try to load from spark.scripts
	if err := viper.UnmarshalKey("spark.scripts", &scripts); err != nil {
		return nil, fmt.Errorf("failed to load scripts from config: %w", err)
	}

	// Also try scripts key (top level)
	if len(scripts) == 0 {
		if err := viper.UnmarshalKey("scripts", &scripts); err != nil {
			return nil, fmt.Errorf("failed to load scripts from config: %w", err)
		}
	}

	return scripts, nil
}

// LoadScriptsFromDir loads scripts from the scripts directory
func (sm *ScriptManager) LoadScriptsFromDir() ([]Script, error) {
	var scripts []Script

	// Check if directory exists
	if _, err := os.Stat(sm.scriptsDir); os.IsNotExist(err) {
		return scripts, nil
	}

	// Read directory
	entries, err := os.ReadDir(sm.scriptsDir)
	if err != nil {
		return nil, fmt.Errorf("failed to read scripts directory: %w", err)
	}

	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}

		name := entry.Name()
		// Check if it's a script file
		if isScriptFile(name) {
			scriptPath := filepath.Join(sm.scriptsDir, name)
			script := Script{
				Name: getScriptNameWithoutExt(name),
				Path: scriptPath,
			}
			scripts = append(scripts, script)
		}
	}

	return scripts, nil
}

// GetAllScripts returns all scripts from both config and directory
func (sm *ScriptManager) GetAllScripts() ([]Script, error) {
	configScripts, err := sm.LoadScriptsFromConfig()
	if err != nil {
		return nil, err
	}

	dirScripts, err := sm.LoadScriptsFromDir()
	if err != nil {
		return nil, err
	}

	// Merge scripts (config scripts take precedence for same names)
	scriptMap := make(map[string]Script)

	// Add directory scripts first
	for _, s := range dirScripts {
		scriptMap[s.Name] = s
	}

	// Override with config scripts
	for _, s := range configScripts {
		if s.Name != "" {
			scriptMap[s.Name] = s
		}
	}

	// Convert back to slice
	var result []Script
	for _, s := range scriptMap {
		result = append(result, s)
	}

	return result, nil
}

// GetScript finds a script by name
func (sm *ScriptManager) GetScript(name string) (*Script, error) {
	scripts, err := sm.GetAllScripts()
	if err != nil {
		return nil, err
	}

	for _, s := range scripts {
		if s.Name == name {
			return &s, nil
		}
	}

	return nil, fmt.Errorf("script '%s' not found", name)
}

// Run executes a script with the given arguments
func (sm *ScriptManager) Run(name string, args []string) error {
	script, err := sm.GetScript(name)
	if err != nil {
		return err
	}

	// Determine how to execute the script
	if script.Path != "" {
		// Execute from file
		return sm.runScriptFile(script.Path, args)
	}

	// Execute from content
	return sm.runScriptContent(script.Content, args, name)
}

func (sm *ScriptManager) runScriptFile(scriptPath string, args []string) error {
	// Check if file exists
	if _, err := os.Stat(scriptPath); os.IsNotExist(err) {
		return fmt.Errorf("script file not found: %s", scriptPath)
	}

	// Make executable on Unix systems
	if runtime.GOOS != "windows" {
		os.Chmod(scriptPath, 0755)
	}

	// Create command
	var cmd *exec.Cmd
	if runtime.GOOS == "windows" {
		// On Windows, use cmd or PowerShell depending on extension
		ext := strings.ToLower(filepath.Ext(scriptPath))
		if ext == ".ps1" {
			cmd = exec.Command("powershell", "-ExecutionPolicy", "Bypass", "-File", scriptPath)
			cmd.Args = append(cmd.Args, args...)
		} else if ext == ".bat" || ext == ".cmd" {
			cmd = exec.Command(scriptPath, args...)
		} else {
			// Assume bash script via WSL or Git Bash
			cmd = exec.Command("bash", append([]string{scriptPath}, args...)...)
		}
	} else {
		// Unix systems
		cmd = exec.Command(scriptPath, args...)
	}

	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin

	return cmd.Run()
}

func (sm *ScriptManager) runScriptContent(content string, args []string, name string) error {
	if content == "" {
		return fmt.Errorf("script '%s' has no content", name)
	}

	// Detect shell from shebang
	shell := "bash"
	lines := strings.Split(content, "\n")
	if len(lines) > 0 && strings.HasPrefix(lines[0], "#!") {
		shebang := lines[0]
		if strings.Contains(shebang, "python") {
			shell = "python"
		} else if strings.Contains(shebang, "node") {
			shell = "node"
		} else if strings.Contains(shebang, "/bin/sh") {
			shell = "sh"
		}
	}

	// Create temporary script file
	tmpDir := os.TempDir()
	var scriptExt string
	if runtime.GOOS == "windows" {
		scriptExt = ".bat"
		if shell == "python" {
			scriptExt = ".py"
		}
	}

	tmpFile := filepath.Join(tmpDir, fmt.Sprintf("spark-script-%s%s", name, scriptExt))
	if err := os.WriteFile(tmpFile, []byte(content), 0755); err != nil {
		return fmt.Errorf("failed to create temporary script: %w", err)
	}
	defer os.Remove(tmpFile)

	// Execute
	return sm.runScriptFile(tmpFile, args)
}

// isScriptFile checks if a file is a script file
func isScriptFile(name string) bool {
	ext := strings.ToLower(filepath.Ext(name))
	scriptExts := []string{".sh", ".bash", ".zsh", ".py", ".rb", ".pl", ".ps1", ".bat", ".cmd"}

	for _, se := range scriptExts {
		if ext == se {
			return true
		}
	}

	// Also check if file has no extension but is executable
	if ext == "" && !strings.HasPrefix(name, ".") {
		return true
	}

	return false
}

// getScriptNameWithoutExt returns the script name without extension
func getScriptNameWithoutExt(name string) string {
	ext := filepath.Ext(name)
	return strings.TrimSuffix(name, ext)
}

// GetScriptType returns the type of script based on extension
func GetScriptType(path string) string {
	ext := strings.ToLower(filepath.Ext(path))
	switch ext {
	case ".sh", ".bash":
		return "bash"
	case ".zsh":
		return "zsh"
	case ".py":
		return "python"
	case ".rb":
		return "ruby"
	case ".pl":
		return "perl"
	case ".ps1":
		return "powershell"
	case ".bat", ".cmd":
		return "batch"
	default:
		return "shell"
	}
}
