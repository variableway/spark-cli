package agent

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
)

type ProfileMeta struct {
	Agent AgentType `json:"agent"`
}

type Profile struct {
	Name string
	Meta ProfileMeta
	Dir  string
}

func (m *Manager) GetProfilesDir() string {
	return filepath.Join(m.homeDir, ".spark", "profiles")
}

func (m *Manager) ListProfiles() ([]Profile, error) {
	profilesDir := m.GetProfilesDir()

	entries, err := os.ReadDir(profilesDir)
	if err != nil {
		if os.IsNotExist(err) {
			return []Profile{}, nil
		}
		return nil, err
	}

	var profiles []Profile
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		name := entry.Name()
		profile, err := m.GetProfile(name)
		if err != nil {
			continue // skip invalid profiles
		}
		profiles = append(profiles, *profile)
	}

	return profiles, nil
}

func (m *Manager) GetProfile(name string) (*Profile, error) {
	dir := filepath.Join(m.GetProfilesDir(), name)
	metaPath := filepath.Join(dir, "meta.json")

	content, err := os.ReadFile(metaPath)
	if err != nil {
		return nil, err
	}

	var meta ProfileMeta
	if err := json.Unmarshal(content, &meta); err != nil {
		return nil, err
	}

	return &Profile{
		Name: name,
		Meta: meta,
		Dir:  dir,
	}, nil
}

func (m *Manager) AddProfile(name string, agent AgentType) error {
	if _, ok := AgentConfigs[agent]; !ok {
		return fmt.Errorf("unknown agent: %s", agent)
	}

	dir := filepath.Join(m.GetProfilesDir(), name)
	if _, err := os.Stat(dir); !os.IsNotExist(err) {
		return fmt.Errorf("profile already exists: %s", name)
	}

	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}

	meta := ProfileMeta{Agent: agent}
	metaBytes, err := json.MarshalIndent(meta, "", "  ")
	if err != nil {
		return err
	}

	if err := os.WriteFile(filepath.Join(dir, "meta.json"), metaBytes, 0644); err != nil {
		return err
	}

	// Create empty files or copy from global
	configPaths, _ := m.GetAgentConfigPath(agent)
	configDef := AgentConfigs[agent]

	for i, relPath := range configDef.ConfigFiles {
		targetPath := filepath.Join(dir, "files", relPath)
		if err := os.MkdirAll(filepath.Dir(targetPath), 0755); err != nil {
			return err
		}

		// Try to copy from global config
		globalPath := configPaths[i]
		if content, err := os.ReadFile(globalPath); err == nil {
			os.WriteFile(targetPath, content, 0644)
		} else {
			// Create empty file
			os.WriteFile(targetPath, []byte{}, 0644)
		}
	}

	return nil
}

func (m *Manager) ViewProfileConfig(name string) (map[string]string, error) {
	profile, err := m.GetProfile(name)
	if err != nil {
		return nil, err
	}

	configDef := AgentConfigs[profile.Meta.Agent]
	results := make(map[string]string)

	for _, relPath := range configDef.ConfigFiles {
		targetPath := filepath.Join(profile.Dir, "files", relPath)
		content, err := os.ReadFile(targetPath)
		if err != nil {
			if os.IsNotExist(err) {
				continue
			}
			return nil, fmt.Errorf("failed to read %s: %w", targetPath, err)
		}
		results[relPath] = string(content)
	}

	return results, nil
}

func (m *Manager) EditProfileConfig(name string, fileIndex int) error {
	profile, err := m.GetProfile(name)
	if err != nil {
		return err
	}

	configDef := AgentConfigs[profile.Meta.Agent]
	if fileIndex < 0 || fileIndex >= len(configDef.ConfigFiles) {
		return fmt.Errorf("invalid config file index: %d", fileIndex)
	}

	targetPath := filepath.Join(profile.Dir, "files", configDef.ConfigFiles[fileIndex])

	cmd := exec.Command(m.editor, targetPath)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

func (m *Manager) ApplyProfile(name string, projectDir string) error {
	profile, err := m.GetProfile(name)
	if err != nil {
		return err
	}

	configDef := AgentConfigs[profile.Meta.Agent]
	for _, relPath := range configDef.ConfigFiles {
		srcPath := filepath.Join(profile.Dir, "files", relPath)
		dstPath := filepath.Join(projectDir, relPath)

		// Check if source file exists and is not empty
		content, err := os.ReadFile(srcPath)
		if err != nil || len(content) == 0 {
			continue // skip empty or non-existent files
		}

		if err := os.MkdirAll(filepath.Dir(dstPath), 0755); err != nil {
			return err
		}

		if err := os.WriteFile(dstPath, content, 0644); err != nil {
			return err
		}
	}

	// Mark current profile and migrate old marker if present
	m.migrateOldAgentMarker(projectDir)
	markerPath := filepath.Join(projectDir, ".spark-agent")
	return os.WriteFile(markerPath, []byte(name), 0644)
}

func (m *Manager) migrateOldAgentMarker(projectDir string) {
	oldMarker := filepath.Join(projectDir, ".monolize-agent")
	newMarker := filepath.Join(projectDir, ".spark-agent")

	if _, err := os.Stat(oldMarker); err == nil {
		if _, err := os.Stat(newMarker); os.IsNotExist(err) {
			os.Rename(oldMarker, newMarker)
		}
	}
}

func (m *Manager) CurrentProfile(projectDir string) (string, error) {
	m.migrateOldAgentMarker(projectDir)
	markerPath := filepath.Join(projectDir, ".spark-agent")
	content, err := os.ReadFile(markerPath)
	if err != nil {
		if os.IsNotExist(err) {
			return "", nil
		}
		return "", err
	}
	return string(content), nil
}
