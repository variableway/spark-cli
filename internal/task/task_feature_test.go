package task

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestInitTaskStructure(t *testing.T) {
	tempDir := t.TempDir()
	mgr := NewManager(tempDir, "", "", false)

	err := mgr.InitTaskStructure()
	if err != nil {
		t.Fatalf("InitTaskStructure failed: %v", err)
	}

	// Check directories were created
	dirs := []string{
		"tasks/features",
		"tasks/config",
		"tasks/analysis",
		"tasks/mindstorm",
		"tasks/planning",
		"tasks/prd",
	}

	for _, dir := range dirs {
		fullPath := filepath.Join(tempDir, dir)
		if _, err := os.Stat(fullPath); os.IsNotExist(err) {
			t.Errorf("Directory not created: %s", dir)
		}
	}

	// Check example file was created
	examplePath := filepath.Join(tempDir, "tasks", "example-feature.md")
	if _, err := os.Stat(examplePath); os.IsNotExist(err) {
		t.Error("example-feature.md not created")
	}
}

func TestInitTaskStructurePreservesExisting(t *testing.T) {
	tempDir := t.TempDir()

	// Create existing directory
	existingDir := filepath.Join(tempDir, "tasks", "features")
	os.MkdirAll(existingDir, 0755)
	existingFile := filepath.Join(existingDir, "existing.md")
	os.WriteFile(existingFile, []byte("existing content"), 0644)

	mgr := NewManager(tempDir, "", "", false)
	err := mgr.InitTaskStructure()
	if err != nil {
		t.Fatalf("InitTaskStructure failed: %v", err)
	}

	// Check existing file is preserved
	content, err := os.ReadFile(existingFile)
	if err != nil {
		t.Errorf("Existing file not preserved: %v", err)
	}
	if string(content) != "existing content" {
		t.Error("Existing file content was modified")
	}
}

func TestCreateFeature(t *testing.T) {
	tempDir := t.TempDir()
	mgr := NewManager(tempDir, "", "", false)

	// Initialize structure first
	mgr.InitTaskStructure()

	// Test creating feature without extension
	err := mgr.CreateFeature("my-feature", "")
	if err != nil {
		t.Fatalf("CreateFeature failed: %v", err)
	}

	featurePath := filepath.Join(tempDir, "tasks", "features", "my-feature.md")
	if _, err := os.Stat(featurePath); os.IsNotExist(err) {
		t.Error("Feature file not created")
	}

	// Test creating feature with extension
	err = mgr.CreateFeature("another.md", "")
	if err != nil {
		t.Fatalf("CreateFeature with extension failed: %v", err)
	}

	anotherPath := filepath.Join(tempDir, "tasks", "features", "another.md")
	if _, err := os.Stat(anotherPath); os.IsNotExist(err) {
		t.Error("Feature file with extension not created")
	}
}

func TestCreateFeatureWithSpaces(t *testing.T) {
	tempDir := t.TempDir()
	mgr := NewManager(tempDir, "", "", false)
	mgr.InitTaskStructure()

	// Test creating feature with spaces in name
	err := mgr.CreateFeature("make script issue", "")
	if err != nil {
		t.Fatalf("CreateFeature with spaces failed: %v", err)
	}

	// Check file was created with dashes instead of spaces
	featurePath := filepath.Join(tempDir, "tasks", "features", "make-script-issue.md")
	if _, err := os.Stat(featurePath); os.IsNotExist(err) {
		t.Error("Feature file with normalized name not created")
	}

	// Check file with spaces does NOT exist
	wrongPath := filepath.Join(tempDir, "tasks", "features", "make script issue.md")
	if _, err := os.Stat(wrongPath); !os.IsNotExist(err) {
		t.Error("Feature file with spaces should not exist")
	}
}

func TestCreateFeatureWithContent(t *testing.T) {
	tempDir := t.TempDir()
	mgr := NewManager(tempDir, "", "", false)
	mgr.InitTaskStructure()

	customContent := "This is a custom description for the feature."
	err := mgr.CreateFeature("custom-content", customContent)
	if err != nil {
		t.Fatalf("CreateFeature with content failed: %v", err)
	}

	featurePath := filepath.Join(tempDir, "tasks", "features", "custom-content.md")
	content, err := os.ReadFile(featurePath)
	if err != nil {
		t.Fatalf("Failed to read feature file: %v", err)
	}

	// Check content is in the file
	if !strings.Contains(string(content), customContent) {
		t.Errorf("Feature content should contain '%s', got:\n%s", customContent, string(content))
	}

	// Check it's in the Description section
	if !strings.Contains(string(content), "## Description") {
		t.Error("Feature should have Description section")
	}
}

func TestCreateFeatureWithUnderscores(t *testing.T) {
	tempDir := t.TempDir()
	mgr := NewManager(tempDir, "", "", false)
	mgr.InitTaskStructure()

	// Test creating feature with underscores
	err := mgr.CreateFeature("my_feature_name", "")
	if err != nil {
		t.Fatalf("CreateFeature with underscores failed: %v", err)
	}

	// Check file was created with dashes instead of underscores
	featurePath := filepath.Join(tempDir, "tasks", "features", "my-feature-name.md")
	if _, err := os.Stat(featurePath); os.IsNotExist(err) {
		t.Error("Feature file with dashes (normalized from underscores) not created")
	}
}

func TestCreateFeatureDuplicate(t *testing.T) {
	tempDir := t.TempDir()
	mgr := NewManager(tempDir, "", "", false)
	mgr.InitTaskStructure()

	// Create first feature
	mgr.CreateFeature("duplicate", "")

	// Try to create duplicate
	err := mgr.CreateFeature("duplicate", "")
	if err == nil {
		t.Error("Expected error for duplicate feature name")
	}
}

func TestCreateFeatureDuplicateWithSpaces(t *testing.T) {
	tempDir := t.TempDir()
	mgr := NewManager(tempDir, "", "", false)
	mgr.InitTaskStructure()

	// Create first feature with spaces
	mgr.CreateFeature("my feature", "")

	// Try to create duplicate with same spaces
	err := mgr.CreateFeature("my feature", "")
	if err == nil {
		t.Error("Expected error for duplicate feature name with spaces")
	}

	// Try to create duplicate with dashes (should also fail)
	err = mgr.CreateFeature("my-feature", "")
	if err == nil {
		t.Error("Expected error for duplicate feature name (spaces vs dashes)")
	}
}

func TestListFeatures(t *testing.T) {
	tempDir := t.TempDir()
	mgr := NewManager(tempDir, "", "", false)
	mgr.InitTaskStructure()

	// Create some features
	mgr.CreateFeature("feature1", "")
	mgr.CreateFeature("feature2", "")

	features, err := mgr.ListFeatures()
	if err != nil {
		t.Fatalf("ListFeatures failed: %v", err)
	}

	if len(features) != 2 {
		t.Errorf("Expected 2 features, got %d", len(features))
	}

	// Check feature names
	found := make(map[string]bool)
	for _, f := range features {
		found[f] = true
	}

	if !found["feature1.md"] {
		t.Error("feature1.md not found in list")
	}
	if !found["feature2.md"] {
		t.Error("feature2.md not found in list")
	}
}

func TestDeleteFeature(t *testing.T) {
	tempDir := t.TempDir()
	mgr := NewManager(tempDir, "", "", false)
	mgr.InitTaskStructure()

	// Create feature
	mgr.CreateFeature("to-delete", "")

	// Verify it exists
	featurePath := filepath.Join(tempDir, "tasks", "features", "to-delete.md")
	if _, err := os.Stat(featurePath); os.IsNotExist(err) {
		t.Fatal("Feature file not created for deletion test")
	}

	// Delete it
	err := mgr.DeleteFeature("to-delete", true)
	if err != nil {
		t.Fatalf("DeleteFeature failed: %v", err)
	}

	// Verify it's gone
	if _, err := os.Stat(featurePath); !os.IsNotExist(err) {
		t.Error("Feature file still exists after deletion")
	}
}

func TestDeleteFeatureWithSpaces(t *testing.T) {
	tempDir := t.TempDir()
	mgr := NewManager(tempDir, "", "", false)
	mgr.InitTaskStructure()

	// Create feature with spaces
	mgr.CreateFeature("delete me", "")

	// Delete using spaces (should be normalized)
	err := mgr.DeleteFeature("delete me", true)
	if err != nil {
		t.Fatalf("DeleteFeature with spaces failed: %v", err)
	}

	// Verify it's gone
	featurePath := filepath.Join(tempDir, "tasks", "features", "delete-me.md")
	if _, err := os.Stat(featurePath); !os.IsNotExist(err) {
		t.Error("Feature file still exists after deletion with spaces")
	}
}

func TestDeleteFeatureNotFound(t *testing.T) {
	tempDir := t.TempDir()
	mgr := NewManager(tempDir, "", "", false)
	mgr.InitTaskStructure()

	err := mgr.DeleteFeature("nonexistent", true)
	if err == nil {
		t.Error("Expected error for non-existent feature")
	}
}

func TestGetFeaturePath(t *testing.T) {
	tempDir := t.TempDir()
	mgr := NewManager(tempDir, "", "", false)
	mgr.InitTaskStructure()
	mgr.CreateFeature("test-feature", "")

	// Test without extension
	path, err := mgr.GetFeaturePath("test-feature")
	if err != nil {
		t.Fatalf("GetFeaturePath failed: %v", err)
	}
	expectedPath := filepath.Join(tempDir, "tasks", "features", "test-feature.md")
	if path != expectedPath {
		t.Errorf("Path mismatch. Got %s, expected %s", path, expectedPath)
	}

	// Test with extension
	path, err = mgr.GetFeaturePath("test-feature.md")
	if err != nil {
		t.Fatalf("GetFeaturePath with extension failed: %v", err)
	}
	if path != expectedPath {
		t.Errorf("Path mismatch with extension. Got %s, expected %s", path, expectedPath)
	}
}

func TestGetFeaturePathWithSpaces(t *testing.T) {
	tempDir := t.TempDir()
	mgr := NewManager(tempDir, "", "", false)
	mgr.InitTaskStructure()
	mgr.CreateFeature("my test feature", "")

	// Get path using spaces
	path, err := mgr.GetFeaturePath("my test feature")
	if err != nil {
		t.Fatalf("GetFeaturePath with spaces failed: %v", err)
	}
	expectedPath := filepath.Join(tempDir, "tasks", "features", "my-test-feature.md")
	if path != expectedPath {
		t.Errorf("Path mismatch with spaces. Got %s, expected %s", path, expectedPath)
	}
}

func TestGetFeaturePathNotFound(t *testing.T) {
	tempDir := t.TempDir()
	mgr := NewManager(tempDir, "", "", false)
	mgr.InitTaskStructure()

	_, err := mgr.GetFeaturePath("nonexistent")
	if err == nil {
		t.Error("Expected error for non-existent feature")
	}
}

func TestGenerateFeatureTemplate(t *testing.T) {
	template := generateFeatureTemplate("my-cool-feature.md")

	// Check title is included
	if !contains(template, "Task: My Cool Feature") {
		t.Error("Template should contain formatted title")
	}

	// Check sections are included
	if !contains(template, "## Description") {
		t.Error("Template should contain Description section")
	}
	if !contains(template, "## Acceptance Criteria") {
		t.Error("Template should contain Acceptance Criteria section")
	}
}

func TestReplaceDescriptionContent(t *testing.T) {
	template := `# Task: Test

## Description

Old description.

## Acceptance Criteria

- [ ] Criteria 1
`

	userContent := "New custom description."
	result := replaceDescriptionContent(template, userContent)

	// Check user content is in result
	if !strings.Contains(result, userContent) {
		t.Errorf("Result should contain user content '%s'", userContent)
	}

	// Check old placeholder is removed (it should be before the new content)
	if strings.Contains(result, "Old description.") {
		t.Error("Old placeholder should be removed")
	}

	// Check section structure is preserved
	if !strings.Contains(result, "## Description") {
		t.Error("Description section should be preserved")
	}
	if !strings.Contains(result, "## Acceptance Criteria") {
		t.Error("Acceptance Criteria section should be preserved")
	}
}

func TestReplaceDescriptionContentChinese(t *testing.T) {
	template := `# 任务：测试

## 描述

旧描述。

## 验收标准

- [ ] 标准 1
`

	userContent := "新的自定义描述。"
	result := replaceDescriptionContent(template, userContent)

	// Check user content is in result
	if !strings.Contains(result, userContent) {
		t.Errorf("Result should contain user content '%s'", userContent)
	}

	// Check old placeholder is removed
	if strings.Contains(result, "旧描述。") {
		t.Error("Old placeholder should be removed")
	}

	// Check section structure is preserved
	if !strings.Contains(result, "## 描述") {
		t.Error("描述 section should be preserved")
	}
	if !strings.Contains(result, "## 验收标准") {
		t.Error("验收标准 section should be preserved")
	}
}

func contains(s, substr string) bool {
	return len(s) > 0 && len(substr) > 0 && (s == substr || len(s) > len(substr) && (s[:len(substr)] == substr || s[len(s)-len(substr):] == substr || containsSubstring(s, substr)))
}

func containsSubstring(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
