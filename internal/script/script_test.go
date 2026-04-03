package script

import (
	"os"
	"path/filepath"
	"testing"
)

func TestGetScriptNameWithoutExt(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"hello.sh", "hello"},
		{"deploy.py", "deploy"},
		{"test-script", "test-script"},
		{"script.with.dots.sh", "script.with.dots"},
	}

	for _, tt := range tests {
		result := getScriptNameWithoutExt(tt.input)
		if result != tt.expected {
			t.Errorf("getScriptNameWithoutExt(%q) = %q, want %q", tt.input, result, tt.expected)
		}
	}
}

func TestIsScriptFile(t *testing.T) {
	tests := []struct {
		input    string
		expected bool
	}{
		{"hello.sh", true},
		{"deploy.py", true},
		{"test.rb", true},
		{"script.ps1", true},
		{"run.bat", true},
		{"command", true},  // No extension
		{".hidden", false}, // Hidden file
		{"readme.txt", false},
		{"data.json", false},
	}

	for _, tt := range tests {
		result := isScriptFile(tt.input)
		if result != tt.expected {
			t.Errorf("isScriptFile(%q) = %v, want %v", tt.input, result, tt.expected)
		}
	}
}

func TestGetScriptType(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"/path/to/script.sh", "bash"},
		{"/path/to/script.bash", "bash"},
		{"/path/to/script.zsh", "zsh"},
		{"/path/to/script.py", "python"},
		{"/path/to/script.rb", "ruby"},
		{"/path/to/script.pl", "perl"},
		{"/path/to/script.ps1", "powershell"},
		{"/path/to/script.bat", "batch"},
		{"/path/to/script.cmd", "batch"},
		{"/path/to/script", "shell"},
	}

	for _, tt := range tests {
		result := GetScriptType(tt.input)
		if result != tt.expected {
			t.Errorf("GetScriptType(%q) = %q, want %q", tt.input, result, tt.expected)
		}
	}
}

func TestScriptManagerLoadScriptsFromDir(t *testing.T) {
	// Create temp directory
	tempDir := t.TempDir()

	// Create test scripts
	testScripts := []struct {
		name    string
		content string
	}{
		{"hello.sh", "#!/bin/bash\necho hello"},
		{"deploy.py", "#!/usr/bin/env python3\nprint('deploy')"},
		{"README.md", "# This should not be loaded"},
	}

	for _, ts := range testScripts {
		path := filepath.Join(tempDir, ts.name)
		if err := os.WriteFile(path, []byte(ts.content), 0755); err != nil {
			t.Fatalf("Failed to create test file: %v", err)
		}
	}

	manager := NewScriptManager(tempDir)
	scripts, err := manager.LoadScriptsFromDir()
	if err != nil {
		t.Fatalf("LoadScriptsFromDir failed: %v", err)
	}

	// Should find 2 scripts (excluding README.md)
	if len(scripts) != 2 {
		t.Errorf("Expected 2 scripts, got %d", len(scripts))
	}

	// Check script names
	scriptMap := make(map[string]bool)
	for _, s := range scripts {
		scriptMap[s.Name] = true
	}

	if !scriptMap["hello"] {
		t.Error("Expected to find 'hello' script")
	}
	if !scriptMap["deploy"] {
		t.Error("Expected to find 'deploy' script")
	}
	if scriptMap["README"] {
		t.Error("Should not find README as a script")
	}
}

func TestScriptManagerGetScript(t *testing.T) {
	// Create temp directory
	tempDir := t.TempDir()

	// Create test script
	scriptPath := filepath.Join(tempDir, "test.sh")
	if err := os.WriteFile(scriptPath, []byte("#!/bin/bash\necho test"), 0755); err != nil {
		t.Fatalf("Failed to create test file: %v", err)
	}

	manager := NewScriptManager(tempDir)

	// Test finding existing script
	s, err := manager.GetScript("test")
	if err != nil {
		t.Errorf("Expected to find 'test' script: %v", err)
	}
	if s == nil {
		t.Error("Expected non-nil script")
	} else if s.Name != "test" {
		t.Errorf("Expected script name 'test', got %q", s.Name)
	}

	// Test finding non-existent script
	_, err = manager.GetScript("nonexistent")
	if err == nil {
		t.Error("Expected error for non-existent script")
	}
}

func TestScriptManagerGetScriptsDir(t *testing.T) {
	manager := NewScriptManager("custom-scripts")
	if manager.GetScriptsDir() != "custom-scripts" {
		t.Error("GetScriptsDir should return the custom directory")
	}

	manager2 := NewScriptManager("")
	if manager2.GetScriptsDir() != "scripts" {
		t.Error("GetScriptsDir should default to 'scripts'")
	}
}
