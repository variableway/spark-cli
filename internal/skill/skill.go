package skill

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"go.yaml.in/yaml/v3"
)

type Skill struct {
	Name        string `json:"name" yaml:"name"`
	Description string `json:"description" yaml:"description"`
	Path        string `json:"path" yaml:"path"`
	Source      string `json:"source" yaml:"source"`
}

type source struct {
	label string
	dir   string
}

func Discover(cwd string) ([]Skill, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return nil, fmt.Errorf("resolve home dir: %w", err)
	}

	sources := []source{
		{"project", filepath.Join(cwd, ".mimocode", "skills")},
		{"project", filepath.Join(cwd, ".mimocode", "skill")},
		{"project", filepath.Join(cwd, ".agents", "skills")},
		{"claude", filepath.Join(home, ".claude", "skills")},
		{"global", filepath.Join(home, ".agents", "skills")},
		{"global", filepath.Join(home, ".mimocode", "skills")},
		{"global", filepath.Join(home, ".mimocode", "skill")},
	}

	builtinRoot := filepath.Join(home, ".local", "share", "mimocode", "builtin_skills")
	entries, err := os.ReadDir(builtinRoot)
	if err == nil {
		versions := make([]string, 0, len(entries))
		for _, e := range entries {
			if e.IsDir() {
				versions = append(versions, e.Name())
			}
		}
		sortVersionsDesc(versions)
		for _, v := range versions {
			sources = append(sources, source{
				label: "builtin:" + v,
				dir:   filepath.Join(builtinRoot, v, "skills"),
			})
		}
	}

	seen := make(map[string]bool)
	var skills []Skill
	for _, s := range sources {
		found, err := scanDir(s.dir, s.label)
		if err != nil {
			continue
		}
		for _, sk := range found {
			if seen[sk.Name] {
				continue
			}
			seen[sk.Name] = true
			skills = append(skills, sk)
		}
	}

	sort.Slice(skills, func(i, j int) bool {
		if skills[i].Source != skills[j].Source {
			return skills[i].Source < skills[j].Source
		}
		return skills[i].Name < skills[j].Name
	})
	return skills, nil
}

func sortVersionsDesc(versions []string) {
	sort.Slice(versions, func(i, j int) bool {
		return compareVersions(versions[i], versions[j]) > 0
	})
}

func compareVersions(a, b string) int {
	as := strings.Split(a, ".")
	bs := strings.Split(b, ".")
	for i := 0; i < len(as) || i < len(bs); i++ {
		var ai, bi int
		if i < len(as) {
			fmt.Sscanf(as[i], "%d", &ai)
		}
		if i < len(bs) {
			fmt.Sscanf(bs[i], "%d", &bi)
		}
		if ai != bi {
			return ai - bi
		}
	}
	return 0
}

func scanDir(dir, label string) ([]Skill, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}

	var skills []Skill
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		skillDir := filepath.Join(dir, e.Name())
		skillMD := filepath.Join(skillDir, "SKILL.md")
		if _, err := os.Stat(skillMD); err != nil {
			continue
		}
		name, desc := parseFrontmatter(skillMD)
		if name == "" {
			name = e.Name()
		}
		skills = append(skills, Skill{
			Name:        name,
			Description: desc,
			Path:        skillDir,
			Source:      label,
		})
	}
	return skills, nil
}

type frontmatter struct {
	Name        string `yaml:"name"`
	Description string `yaml:"description"`
}

func parseFrontmatter(skillMD string) (name, description string) {
	f, err := os.Open(skillMD)
	if err != nil {
		return "", ""
	}
	defer f.Close()

	data, err := io.ReadAll(io.LimitReader(f, 64*1024))
	if err != nil {
		return "", ""
	}

	text := string(data)
	if !strings.HasPrefix(text, "---\n") {
		return "", ""
	}
	rest := text[4:]
	end := strings.Index(rest, "\n---")
	if end < 0 {
		return "", ""
	}

	var fm frontmatter
	if err := yaml.Unmarshal([]byte(rest[:end]), &fm); err != nil {
		return "", ""
	}
	return fm.Name, fm.Description
}

func Sync(skills []Skill, targetDir string, clear bool) ([]string, error) {
	if clear {
		if err := clearDir(targetDir); err != nil {
			return nil, err
		}
	}

	if err := os.MkdirAll(targetDir, 0755); err != nil {
		return nil, fmt.Errorf("create target dir: %w", err)
	}

	var copied []string
	used := make(map[string]bool)
	for _, s := range skills {
		name := s.Name
		if used[name] {
			name = s.Name + "-" + s.Source
		}
		for i := 2; used[name]; i++ {
			name = fmt.Sprintf("%s-%s-%d", s.Name, s.Source, i)
		}
		used[name] = true

		dest := filepath.Join(targetDir, name)
		if err := copyDir(s.Path, dest); err != nil {
			return copied, fmt.Errorf("copy %s: %w", s.Name, err)
		}
		copied = append(copied, dest)
	}
	return copied, nil
}

func clearDir(dir string) error {
	entries, err := os.ReadDir(dir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return fmt.Errorf("read target dir: %w", err)
	}
	for _, e := range entries {
		if err := os.RemoveAll(filepath.Join(dir, e.Name())); err != nil {
			return fmt.Errorf("remove %s: %w", e.Name(), err)
		}
	}
	return nil
}

func copyDir(src, dest string) error {
	info, err := os.Stat(src)
	if err != nil {
		return err
	}
	if !info.IsDir() {
		return fmt.Errorf("%s is not a directory", src)
	}

	if err := os.MkdirAll(dest, info.Mode().Perm()); err != nil {
		return err
	}

	entries, err := os.ReadDir(src)
	if err != nil {
		return err
	}
	for _, e := range entries {
		srcPath := filepath.Join(src, e.Name())
		destPath := filepath.Join(dest, e.Name())
		if e.IsDir() {
			if err := copyDir(srcPath, destPath); err != nil {
				return err
			}
			continue
		}
		if err := copyFile(srcPath, destPath); err != nil {
			return err
		}
	}
	return nil
}

func copyFile(src, dest string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	info, err := in.Stat()
	if err != nil {
		return err
	}

	out, err := os.OpenFile(dest, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, info.Mode().Perm())
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, in)
	return err
}
