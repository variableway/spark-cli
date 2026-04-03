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

	// Normalize filename: replace spaces with dashes
	name = strings.TrimSpace(name)
	name = strings.ReplaceAll(name, " ", "-")
	name = strings.ReplaceAll(name, "_", "-")

	// Add .md extension if not present
	if !strings.HasSuffix(name, ".md") {
		name = name + ".md"
	}

	featurePath := filepath.Join(featuresDir, name)

	// Check if file already exists
	if _, err := os.Stat(featurePath); err == nil {
		return fmt.Errorf("feature file already exists: %s", name)
	}

	// Generate file content from template with content parameter
	fileContent := generateFeatureContent(name, content)

	// Write file
	if err := os.WriteFile(featurePath, []byte(fileContent), 0644); err != nil {
		return fmt.Errorf("failed to create feature file: %w", err)
	}

	m.UI.Success(fmt.Sprintf("Created feature: %s", name))
	m.UI.Printf("  Path: %s\n", featurePath)

	return nil
}

// DeleteFeature deletes a feature file
func (m *Manager) DeleteFeature(name string, force bool) error {
	featuresDir := filepath.Join(m.TaskDir, "tasks", "features")

	// Normalize filename: replace spaces with dashes
	name = strings.TrimSpace(name)
	name = strings.ReplaceAll(name, " ", "-")
	name = strings.ReplaceAll(name, "_", "-")

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
	// Normalize filename: replace spaces with dashes
	name = strings.TrimSpace(name)
	name = strings.ReplaceAll(name, " ", "-")
	name = strings.ReplaceAll(name, "_", "-")

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

// generateFeatureContent generates feature content from template and user content
func generateFeatureContent(name string, userContent string) string {
	// Try to read example-feature.md template
	templateContent := ""
	examplePath := filepath.Join("tasks", "example-feature.md")
	
	// Try different paths to find example-feature.md
	possiblePaths := []string{
		examplePath,
		filepath.Join("..", examplePath),
		filepath.Join(".", examplePath),
	}
	
	for _, path := range possiblePaths {
		if data, err := os.ReadFile(path); err == nil {
			templateContent = string(data)
			break
		}
	}
	
	// If template not found, use default
	if templateContent == "" {
		templateContent = DefaultExampleFeature
	}
	
	// Replace title placeholder
	baseName := strings.TrimSuffix(name, ".md")
	baseName = strings.ReplaceAll(baseName, "-", " ")
	baseName = strings.Title(baseName)
	
	content := strings.ReplaceAll(templateContent, "Example Feature", baseName)
	content = strings.ReplaceAll(content, "# Task: Example Feature", fmt.Sprintf("# Task: %s", baseName))
	
	// If user provided content, replace or insert into Description section
	if userContent != "" {
		content = replaceDescriptionContent(content, userContent)
	}
	
	// Add creation timestamp
	content = content + fmt.Sprintf("\n---\n*Created: %s*\n", time.Now().Format("2006-01-02 15:04:05"))
	
	return content
}

// replaceDescriptionContent replaces the content in Description section with user content
func replaceDescriptionContent(template string, userContent string) string {
	// Support both English and Chinese section headers
	// Find ## Description or ## 描述 section
	descMarkers := []string{"## Description", "## 描述"}
	
	var descIndex int = -1
	var foundMarker string
	
	for _, marker := range descMarkers {
		if idx := strings.Index(template, marker); idx != -1 {
			descIndex = idx
			foundMarker = marker
			break
		}
	}
	
	if descIndex == -1 {
		// No description section found, append at end
		return template + "\n\n## Description\n\n" + userContent + "\n"
	}

	// Find the start of content after the marker
	contentStart := descIndex + len(foundMarker)
	
	// Find the next section (any line starting with ##)
	lines := strings.Split(template[contentStart:], "\n")
	contentEndOffset := 0
	
	for i, line := range lines {
		trimmed := strings.TrimSpace(line)
		if i > 0 && strings.HasPrefix(trimmed, "## ") {
			// Found next section
			for j := 0; j < i; j++ {
				contentEndOffset += len(lines[j]) + 1 // +1 for newline
			}
			break
		}
	}
	
	if contentEndOffset == 0 {
		// No next section found, use rest of template
		contentEndOffset = len(template) - contentStart
	}
	
	// Build new content
	before := template[:contentStart] // Include marker
	after := template[contentStart+contentEndOffset:]
	
	return before + "\n\n" + userContent + "\n" + after
}


