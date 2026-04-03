package task

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// DefaultTaskStructure defines the default task directory structure
var DefaultTaskStructure = []string{
	"tasks/features",
	"tasks/config",
	"tasks/analysis",
	"tasks/mindstorm",
	"tasks/planning",
	"tasks/prd",
}

// DefaultExampleFeature is the default example feature template
var DefaultExampleFeature = `# Task: Example Feature

## Description

Describe your feature here.

## Acceptance Criteria

- [ ] Criteria 1
- [ ] Criteria 2
- [ ] Criteria 3

## Notes

Add any additional notes here.
`

// InitTaskStructure initializes the task directory structure
func (m *Manager) InitTaskStructure() error {
	created := make([]string, 0)
	existing := make([]string, 0)

	for _, dir := range DefaultTaskStructure {
		fullPath := filepath.Join(m.TaskDir, dir)
		if _, err := os.Stat(fullPath); os.IsNotExist(err) {
			if err := os.MkdirAll(fullPath, 0755); err != nil {
				return fmt.Errorf("failed to create directory %s: %w", dir, err)
			}
			created = append(created, dir)
		} else {
			existing = append(existing, dir)
		}
	}

	// Create example-feature.md in tasks/ directory
	examplePath := filepath.Join(m.TaskDir, "tasks", "example-feature.md")
	if _, err := os.Stat(examplePath); os.IsNotExist(err) {
		if err := os.WriteFile(examplePath, []byte(DefaultExampleFeature), 0644); err != nil {
			return fmt.Errorf("failed to create example-feature.md: %w", err)
		}
		created = append(created, "tasks/example-feature.md")
	} else {
		existing = append(existing, "tasks/example-feature.md")
	}

	// Print summary
	if len(created) > 0 {
		m.UI.Success("Created directories and files:")
		for _, item := range created {
			m.UI.Printf("  ✓ %s\n", item)
		}
	}

	if len(existing) > 0 {
		m.UI.Info("Already exists (skipped):")
		for _, item := range existing {
			m.UI.Printf("  • %s\n", item)
		}
	}

	return nil
}

// ListFeatures lists all features in the tasks/features directory
func (m *Manager) ListFeatures() ([]string, error) {
	featuresDir := filepath.Join(m.TaskDir, "tasks", "features")

	if _, err := os.Stat(featuresDir); os.IsNotExist(err) {
		return nil, fmt.Errorf("features directory not found: %s", featuresDir)
	}

	entries, err := os.ReadDir(featuresDir)
	if err != nil {
		return nil, fmt.Errorf("failed to read features directory: %w", err)
	}

	var features []string
	for _, entry := range entries {
		if !entry.IsDir() && strings.HasSuffix(entry.Name(), ".md") {
			features = append(features, entry.Name())
		}
	}

	return features, nil
}

// CreateFeature creates a new feature file
func (m *Manager) CreateFeature(name string, content string) error {
	featuresDir := filepath.Join(m.TaskDir, "tasks", "features")

	// Ensure features directory exists
	if err := os.MkdirAll(featuresDir, 0755); err != nil {
		return fmt.Errorf("failed to create features directory: %w", err)
	}

	// Add .md extension if not present
	if !strings.HasSuffix(name, ".md") {
		name = name + ".md"
	}

	featurePath := filepath.Join(featuresDir, name)

	// Check if file already exists
	if _, err := os.Stat(featurePath); err == nil {
		return fmt.Errorf("feature file already exists: %s", name)
	}

	// If content is empty, use template
	if content == "" {
		content = generateFeatureTemplate(name)
	}

	// Write file
	if err := os.WriteFile(featurePath, []byte(content), 0644); err != nil {
		return fmt.Errorf("failed to create feature file: %w", err)
	}

	m.UI.Success(fmt.Sprintf("Created feature: %s", name))
	m.UI.Printf("  Path: %s\n", featurePath)

	return nil
}

// DeleteFeature deletes a feature file
func (m *Manager) DeleteFeature(name string, force bool) error {
	featuresDir := filepath.Join(m.TaskDir, "tasks", "features")

	// Add .md extension if not present
	if !strings.HasSuffix(name, ".md") {
		name = name + ".md"
	}

	featurePath := filepath.Join(featuresDir, name)

	// Check if file exists
	if _, err := os.Stat(featurePath); os.IsNotExist(err) {
		return fmt.Errorf("feature file not found: %s", name)
	}

	// Delete file
	if err := os.Remove(featurePath); err != nil {
		return fmt.Errorf("failed to delete feature file: %w", err)
	}

	m.UI.Success(fmt.Sprintf("Deleted feature: %s", name))

	return nil
}

// GetFeaturePath returns the full path of a feature file
func (m *Manager) GetFeaturePath(name string) (string, error) {
	// Add .md extension if not present
	if !strings.HasSuffix(name, ".md") {
		name = name + ".md"
	}

	featurePath := filepath.Join(m.TaskDir, "tasks", "features", name)

	if _, err := os.Stat(featurePath); os.IsNotExist(err) {
		return "", fmt.Errorf("feature file not found: %s", name)
	}

	return featurePath, nil
}

// generateFeatureTemplate generates a feature template with the given name
func generateFeatureTemplate(name string) string {
	baseName := strings.TrimSuffix(name, ".md")
	baseName = strings.ReplaceAll(baseName, "-", " ")
	baseName = strings.Title(baseName)

	return fmt.Sprintf(`# Task: %s

## Description

Describe your feature here.

## Acceptance Criteria

- [ ] Criteria 1
- [ ] Criteria 2
- [ ] Criteria 3

## Notes

Add any additional notes here.

---
*Created: %s*
`, baseName, time.Now().Format("2006-01-02 15:04:05"))
}
