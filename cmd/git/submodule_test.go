package git

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestAddNestedRepos(t *testing.T) {
	parent := t.TempDir()
	research := filepath.Join(parent, "research")

	initRepo := func(path, origin string) {
		run := func(args ...string) {
			cmd := exec.Command("git", args...)
			cmd.Dir = path
			if out, err := cmd.CombinedOutput(); err != nil {
				t.Fatalf("git %v: %v\n%s", args, err, out)
			}
		}
		run("init")
		run("config", "user.email", "t@t.com")
		run("config", "user.name", "t")
		run("remote", "add", "origin", origin)
		run("commit", "--allow-empty", "-m", "init")
	}

	initRepo(parent, "https://github.com/variableway/innate-workspace.git")
	repos := []string{"Hatano-Nelson", "CrouzeixConjecture"}
	for _, name := range repos {
		if err := os.MkdirAll(filepath.Join(research, name), 0755); err != nil {
			t.Fatalf("mkdir: %v", err)
		}
		initRepo(filepath.Join(research, name), "https://github.com/jinshanmu/"+name+".git")
	}

	if err := addNestedRepos(parent, research); err != nil {
		t.Fatalf("addNestedRepos: %v", err)
	}

	gm, err := os.ReadFile(filepath.Join(parent, ".gitmodules"))
	if err != nil {
		t.Fatalf("read .gitmodules: %v", err)
	}
	for _, name := range repos {
		path := filepath.Join("research", name)
		if !strings.Contains(string(gm), fmt.Sprintf("path = %s", path)) {
			t.Errorf(".gitmodules missing entry for %s:\n%s", path, gm)
		}
	}

	stage := exec.Command("git", "ls-files", "--stage")
	stage.Dir = parent
	out, err := stage.Output()
	if err != nil {
		t.Fatalf("ls-files --stage: %v", err)
	}
	for _, name := range repos {
		path := filepath.Join("research", name)
		if !strings.Contains(string(out), "160000") || !strings.Contains(string(out), "\t"+path) {
			t.Errorf("expected gitlink for %s, got:\n%s", path, out)
		}
	}

	if _, err := os.Stat(filepath.Join(parent, "Hatano-Nelson")); !os.IsNotExist(err) {
		t.Errorf("unexpected clone at parent root: %v", err)
	}

	if err := addNestedRepos(parent, research); err != nil {
		t.Fatalf("addNestedRepos rerun: %v", err)
	}
	gm2, err := os.ReadFile(filepath.Join(parent, ".gitmodules"))
	if err != nil {
		t.Fatalf("read .gitmodules after rerun: %v", err)
	}
	if got := strings.Count(string(gm2), "[submodule"); got != len(repos) {
		t.Errorf("expected %d submodule entries after rerun, got %d:\n%s", len(repos), got, gm2)
	}
}
