package task

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// ImplOptions contains options for task implementation
type ImplOptions struct {
	UseKimi        bool
	UseGitHubWorkflow bool
	AutoComplete   bool
}

// ImplFeature implements a feature using kimi CLI or github-task-workflow
func (m *Manager) ImplFeature(name string, opts ImplOptions) error {
	// Get feature file path
	featurePath, err := m.GetFeaturePath(name)
	if err != nil {
		return err
	}

	m.UI.Success(fmt.Sprintf("Implementing feature: %s", name))
	m.UI.Printf("  Path: %s\n", featurePath)

	// Check if kim CLI is available
	kimiAvailable := isCommandAvailable("kimi")
	if !kimiAvailable {
		m.UI.Warning("kimi CLI not found, falling back to manual execution")
		return m.implManual(featurePath)
	}

	// Use kim CLI with github-task-workflow
	if opts.UseGitHubWorkflow {
		return m.implWithGitHubWorkflow(featurePath)
	}

	// Use kim CLI directly
	return m.implWithKimi(featurePath)
}

// implWithKimi implements feature using kimi CLI directly
func (m *Manager) implWithKimi(featurePath string) error {
	// Read feature content
	content, err := os.ReadFile(featurePath)
	if err != nil {
		return fmt.Errorf("failed to read feature file: %w", err)
	}

	// Create a prompt for kimi
	prompt := fmt.Sprintf("Please execute the following task file and implement the feature. Follow the GitHub Task Workflow: read the task, create an issue, implement the feature, update the issue, and commit the code.\n\nTask file path: %s\n\nTask content:\n%s", featurePath, string(content))

	// Execute kimi
	cmd := exec.Command("kimi", "-c", prompt)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin

	m.UI.Info("Executing with kimi CLI...")
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("kimi execution failed: %w", err)
	}

	return nil
}

// implWithGitHubWorkflow implements feature using github-task-workflow
func (m *Manager) implWithGitHubWorkflow(featurePath string) error {
	// Check if github-task-workflow scripts exist
	workflowDir := filepath.Join("github-task-workflow", "scripts")
	orchestratePath := filepath.Join(workflowDir, "orchestrate.py")

	if _, err := os.Stat(orchestratePath); os.IsNotExist(err) {
		// Try to find it in other locations
		orchestratePath = "/Users/patrick/workspace/variableway/innate/spark-cli/github-task-workflow/scripts/orchestrate.py"
		if _, err := os.Stat(orchestratePath); os.IsNotExist(err) {
			return fmt.Errorf("github-task-workflow not found, please ensure it's installed")
		}
	}

	m.UI.Info("Using github-task-workflow for task implementation")

	// Step 1: Initialize workflow
	m.UI.Info("Step 1/3: Initializing workflow...")
	cmd := exec.Command("python", orchestratePath, "init", featurePath)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to initialize workflow: %w", err)
	}

	// Step 2: Kimi implements the task (user needs to do this manually or via kim CLI)
	m.UI.Info("Step 2/3: Implementing feature...")
	m.UI.Info("Please review the created issue and implement the feature.")
	m.UI.Info("Press Enter when done...")
	fmt.Scanln()

	// Step 3: Finish workflow
	m.UI.Info("Step 3/3: Finishing workflow...")
	cmd = exec.Command("python", orchestratePath, "finish")
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to finish workflow: %w", err)
	}

	m.UI.Success("Feature implementation completed!")
	return nil
}

// implManual provides manual instructions for implementation
func (m *Manager) implManual(featurePath string) error {
	m.UI.Info("Manual Implementation Mode")
	m.UI.Info("=========================")
	m.UI.Printf("Feature file: %s\n", featurePath)
	m.UI.Info("")
	m.UI.Info("To implement this feature manually:")
	m.UI.Info("1. Read the task file:")
	m.UI.Printf("   cat %s\n", featurePath)
	m.UI.Info("")
	m.UI.Info("2. Create a GitHub issue for the task")
	m.UI.Info("")
	m.UI.Info("3. Implement the feature following the acceptance criteria")
	m.UI.Info("")
	m.UI.Info("4. Update the issue and commit your changes")
	m.UI.Info("")
	m.UI.Info("Or install kim CLI for automated execution:")
	m.UI.Info("   https://github.com/kimi-cli/kimi")

	return nil
}

// isCommandAvailable checks if a command is available in PATH
func isCommandAvailable(name string) bool {
	cmd := exec.Command("which", name)
	if err := cmd.Run(); err != nil {
		return false
	}
	return true
}

// RunFeature runs a feature implementation in TUI or CLI mode
func (m *Manager) RunFeature(name string, useTUI bool) error {
	opts := ImplOptions{
		UseKimi:           true,
		UseGitHubWorkflow: true,
		AutoComplete:      true,
	}

	if useTUI {
		// TUI mode implementation
		return m.runFeatureTUI(name, opts)
	}

	return m.ImplFeature(name, opts)
}

// runFeatureTUI runs feature implementation in TUI mode
func (m *Manager) runFeatureTUI(name string, opts ImplOptions) error {
	m.UI.Header("Feature Implementation")

	// Show feature details
	featurePath, err := m.GetFeaturePath(name)
	if err != nil {
		return err
	}

	content, err := os.ReadFile(featurePath)
	if err != nil {
		return fmt.Errorf("failed to read feature file: %w", err)
	}

	m.UI.Info("Feature Details")
	m.UI.Printf("Name: %s\n", name)
	m.UI.Printf("Path: %s\n", featurePath)
	m.UI.Println("")

	// Show preview of content (first 10 lines)
	lines := strings.Split(string(content), "\n")
	previewLines := 10
	if len(lines) < previewLines {
		previewLines = len(lines)
	}

	m.UI.Info("Content Preview:")
	for i := 0; i < previewLines; i++ {
		m.UI.Printf("  %s\n", lines[i])
	}
	if len(lines) > previewLines {
		m.UI.Printf("  ... (%d more lines)\n", len(lines)-previewLines)
	}
	m.UI.Println("")

	// Confirm execution
	confirmed := m.UI.Confirm("Start implementation?")
	if !confirmed {
		m.UI.Info("Implementation cancelled.")
		return nil
	}

	return m.ImplFeature(name, opts)
}
