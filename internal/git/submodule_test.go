package git_test

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"spark/internal/git"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("Submodule", func() {
	var tempDir string

	BeforeEach(func() {
		var err error
		tempDir, err = os.MkdirTemp("", "git-submodule-test")
		Expect(err).NotTo(HaveOccurred())
	})

	AfterEach(func() {
		os.RemoveAll(tempDir)
	})

	// initRepo creates a git repo at path with the optional origin URL and a
	// single committed file, returning its HEAD commit SHA.
	initRepo := func(path, originURL string) string {
		Expect(os.MkdirAll(path, 0755)).To(Succeed())
		run := func(args ...string) []byte {
			cmd := exec.Command("git", args...)
			cmd.Dir = path
			out, err := cmd.CombinedOutput()
			ExpectWithOffset(1, err).NotTo(HaveOccurred(), string(out))
			return out
		}
		run("init")
		run("config", "user.email", "t@t.com")
		run("config", "user.name", "t")
		if originURL != "" {
			run("remote", "add", "origin", originURL)
		}
		Expect(os.WriteFile(filepath.Join(path, "file.txt"), []byte("x"), 0644)).To(Succeed())
		run("add", ".")
		run("commit", "-m", "init")
		return strings.TrimSpace(string(run("rev-parse", "HEAD")))
	}

	Describe("AddExistingRepoAsSubmodule", func() {
		const (
			name = "TradingAgents-astock"
			url  = "https://github.com/AI4Finance-Foundation/TradingAgents.git"
		)

		Context("when the child directory is untracked by the parent", func() {
			It("registers it as a submodule via .gitmodules", func() {
				parent := filepath.Join(tempDir, "parent")
				child := filepath.Join(parent, name)
				initRepo(parent, "")
				head := initRepo(child, url)

				Expect(git.AddExistingRepoAsSubmodule(parent, name, url)).To(Succeed())

				By("writing the .gitmodules entry")
				gm, err := os.ReadFile(filepath.Join(parent, ".gitmodules"))
				Expect(err).NotTo(HaveOccurred())
				Expect(string(gm)).To(ContainSubstring(`[submodule "` + name + `"]`))
				Expect(string(gm)).To(ContainSubstring("path = " + name))
				Expect(string(gm)).To(ContainSubstring("url = " + url))

				By("staging the directory as a gitlink")
				stage := exec.Command("git", "ls-files", "--stage", name)
				stage.Dir = parent
				stageOut, err := stage.Output()
				Expect(err).NotTo(HaveOccurred())
				Expect(string(stageOut)).To(HavePrefix("160000 "))
				Expect(string(stageOut)).To(ContainSubstring(head))

				By("registering the URL in .git/config")
				cfg := exec.Command("git", "config", "--get", fmt.Sprintf("submodule.%s.url", name))
				cfg.Dir = parent
				cfgOut, err := cfg.Output()
				Expect(err).NotTo(HaveOccurred())
				Expect(strings.TrimSpace(string(cfgOut))).To(Equal(url))

				By("appearing in git submodule status")
				st := exec.Command("git", "submodule", "status")
				st.Dir = parent
				stOut, err := st.Output()
				Expect(err).NotTo(HaveOccurred())
				Expect(string(stOut)).To(ContainSubstring(name))
			})
		})

		Context("when the child is already committed by the parent as a gitlink", func() {
			It("adds the .gitmodules entry without moving the pointer", func() {
				parent := filepath.Join(tempDir, "parent")
				child := filepath.Join(parent, name)
				initRepo(parent, "")
				head := initRepo(child, url)

				// Parent commits the embedded repo as a gitlink first.
				add := exec.Command("git", "add", name)
				add.Dir = parent
				Expect(add.Run()).To(Succeed())
				commit := exec.Command("git", "commit", "-m", "track child")
				commit.Dir = parent
				Expect(commit.Run()).To(Succeed())

				Expect(git.AddExistingRepoAsSubmodule(parent, name, url)).To(Succeed())

				By("writing the .gitmodules entry")
				gm, err := os.ReadFile(filepath.Join(parent, ".gitmodules"))
				Expect(err).NotTo(HaveOccurred())
				Expect(string(gm)).To(ContainSubstring(`[submodule "` + name + `"]`))

				By("keeping the gitlink pointing at the child HEAD")
				stage := exec.Command("git", "ls-files", "--stage", name)
				stage.Dir = parent
				stageOut, err := stage.Output()
				Expect(err).NotTo(HaveOccurred())
				Expect(string(stageOut)).To(ContainSubstring(head))
			})
		})

		It("is idempotent and does not duplicate the .gitmodules entry", func() {
			parent := filepath.Join(tempDir, "parent")
			child := filepath.Join(parent, name)
			initRepo(parent, "")
			initRepo(child, url)

			Expect(git.AddExistingRepoAsSubmodule(parent, name, url)).To(Succeed())
			Expect(git.AddExistingRepoAsSubmodule(parent, name, url)).To(Succeed())

			gm, err := os.ReadFile(filepath.Join(parent, ".gitmodules"))
			Expect(err).NotTo(HaveOccurred())
			Expect(strings.Count(string(gm), `[submodule "`+name+`"]`)).To(Equal(1))
		})
	})
})
