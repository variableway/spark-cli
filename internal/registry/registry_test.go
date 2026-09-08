package registry_test

import (
	"os"
	"path/filepath"

	"spark/internal/registry"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

func writeGitRepo(root, name, remoteURL string) string {
	repoPath := filepath.Join(root, name)
	Expect(os.MkdirAll(filepath.Join(repoPath, ".git"), 0755)).To(Succeed())

	config := `[remote "origin"]` + "\n\turl = " + remoteURL + "\n"
	Expect(os.WriteFile(filepath.Join(repoPath, ".git", "config"), []byte(config), 0644)).To(Succeed())

	return repoPath
}

var _ = Describe("Registry", func() {
	var tempDir string

	BeforeEach(func() {
		var err error
		tempDir, err = os.MkdirTemp("", "registry-test")
		Expect(err).NotTo(HaveOccurred())
	})

	AfterEach(func() {
		os.RemoveAll(tempDir)
	})

	Describe("Scan", func() {
		It("finds repositories with an origin remote", func() {
			writeGitRepo(tempDir, "spark-cli", "https://github.com/variableway/spark-cli.git")
			writeGitRepo(tempDir, "demo", "git@github.com:acme/demo.git")

			projects, err := registry.Scan(tempDir)
			Expect(err).NotTo(HaveOccurred())
			Expect(projects).To(HaveLen(2))

			byPath := map[string]registry.Project{}
			for _, p := range projects {
				byPath[p.Path] = p
			}

			Expect(byPath["spark-cli"].Name).To(Equal("spark-cli"))
			Expect(byPath["spark-cli"].Repo).To(Equal("https://github.com/variableway/spark-cli.git"))
			Expect(byPath["demo"].Repo).To(Equal("https://github.com/acme/demo.git"))
		})

		It("skips repositories without an origin remote", func() {
			repoPath := filepath.Join(tempDir, "local-only")
			Expect(os.MkdirAll(filepath.Join(repoPath, ".git"), 0755)).To(Succeed())

			projects, err := registry.Scan(tempDir)
			Expect(err).NotTo(HaveOccurred())
			Expect(projects).To(BeEmpty())
		})

		It("skips hidden and ignored directories", func() {
			writeGitRepo(filepath.Join(tempDir, ".hidden"), "repo", "https://github.com/a/b.git")
			writeGitRepo(filepath.Join(tempDir, "node_modules", "pkg"), "pkg", "https://github.com/a/pkg.git")

			projects, err := registry.Scan(tempDir)
			Expect(err).NotTo(HaveOccurred())
			Expect(projects).To(BeEmpty())
		})

		It("records nested repositories with slash-separated relative paths", func() {
			writeGitRepo(filepath.Join(tempDir, "apps", "tooling"), "spark-cli", "https://github.com/variableway/spark-cli.git")

			projects, err := registry.Scan(tempDir)
			Expect(err).NotTo(HaveOccurred())
			Expect(projects).To(HaveLen(1))
			Expect(projects[0].Path).To(Equal("apps/tooling/spark-cli"))
		})
	})

	Describe("Read and Write", func() {
		It("round-trips projects through yaml", func() {
			path := filepath.Join(tempDir, "registry_demo.yaml")
			reg := &registry.Registry{Projects: []registry.Project{
				{Name: "spark-cli", Repo: "https://github.com/variableway/spark-cli.git", Path: "tooling/spark-cli"},
			}}

			Expect(registry.Write(path, reg)).To(Succeed())

			got, err := registry.Read(path)
			Expect(err).NotTo(HaveOccurred())
			Expect(got.Projects).To(Equal(reg.Projects))
		})

		It("returns an empty registry for a missing file", func() {
			got, err := registry.Read(filepath.Join(tempDir, "missing.yaml"))
			Expect(err).NotTo(HaveOccurred())
			Expect(got.Projects).To(BeEmpty())
		})
	})

	Describe("Merge", func() {
		It("preserves descriptions, drops missing entries and appends new ones", func() {
			existing := []registry.Project{
				{Name: "spark-cli", Repo: "https://github.com/variableway/spark-cli.git", Path: "tooling/spark-cli", Desc: "keep me"},
				{Name: "gone", Repo: "https://github.com/variableway/gone.git", Path: "gone"},
			}
			discovered := []registry.Project{
				{Name: "spark-cli", Repo: "https://github.com/variableway/spark-cli.git", Path: "tooling/spark-cli"},
				{Name: "new", Repo: "https://github.com/variableway/new.git", Path: "new"},
			}

			merged := registry.Merge(existing, discovered)
			Expect(merged).To(HaveLen(2))

			byName := map[string]registry.Project{}
			for _, p := range merged {
				byName[p.Name] = p
			}

			Expect(byName["spark-cli"].Desc).To(Equal("keep me"))
			Expect(byName).To(HaveKey("new"))
			Expect(byName).NotTo(HaveKey("gone"))
		})

		It("updates the path when a repository moves and matches by URL", func() {
			existing := []registry.Project{
				{Name: "spark-cli", Repo: "https://github.com/variableway/spark-cli.git", Path: "old/spark-cli", Desc: "desc"},
			}
			discovered := []registry.Project{
				{Name: "spark-cli", Repo: "https://github.com/variableway/spark-cli.git", Path: "new/spark-cli"},
			}

			merged := registry.Merge(existing, discovered)
			Expect(merged).To(HaveLen(1))
			Expect(merged[0].Path).To(Equal("new/spark-cli"))
			Expect(merged[0].Desc).To(Equal("desc"))
		})

		It("deduplicates by URL when the same repo appears at multiple paths", func() {
			discovered := []registry.Project{
				{Name: "a", Repo: "https://github.com/x/y.git", Path: "one/a"},
				{Name: "b", Repo: "https://github.com/x/y", Path: "two/b"},
			}

			merged := registry.Merge(nil, discovered)
			Expect(merged).To(HaveLen(1))
		})
	})

	Describe("FindByName", func() {
		It("finds a project by name", func() {
			reg := &registry.Registry{Projects: []registry.Project{
				{Name: "spark-cli", Repo: "https://github.com/variableway/spark-cli.git", Path: "tooling/spark-cli"},
			}}

			p, err := registry.FindByName(reg, "spark-cli")
			Expect(err).NotTo(HaveOccurred())
			Expect(p.Repo).To(Equal("https://github.com/variableway/spark-cli.git"))
		})

		It("returns an error when not found", func() {
			reg := &registry.Registry{}
			_, err := registry.FindByName(reg, "missing")
			Expect(err).To(HaveOccurred())
		})
	})

	Describe("TargetPath", func() {
		It("joins root with the project path", func() {
			p := registry.Project{Name: "spark-cli", Path: "tooling/spark-cli"}
			Expect(registry.TargetPath("innate-apps", p)).To(Equal(filepath.Join("innate-apps", "tooling", "spark-cli")))
		})

		It("falls back to the project name when path is empty", func() {
			p := registry.Project{Name: "spark-cli"}
			Expect(registry.TargetPath("innate-apps", p)).To(Equal(filepath.Join("innate-apps", "spark-cli")))
		})
	})
})
