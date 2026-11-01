package collection_test

import (
	"encoding/json"
	"os"
	"path/filepath"

	"spark/internal/collection"
	"spark/internal/github"

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

var _ = Describe("Collection", func() {
	Describe("ParseGitHubRepo", func() {
		It("parses https URLs", func() {
			owner, repo, ok := collection.ParseGitHubRepo("https://github.com/variableway/spark-cli.git")
			Expect(ok).To(BeTrue())
			Expect(owner).To(Equal("variableway"))
			Expect(repo).To(Equal("spark-cli"))
		})

		It("parses SSH URLs", func() {
			owner, repo, ok := collection.ParseGitHubRepo("git@github.com:acme/demo.git")
			Expect(ok).To(BeTrue())
			Expect(owner).To(Equal("acme"))
			Expect(repo).To(Equal("demo"))
		})

		It("parses URLs without .git suffix", func() {
			owner, repo, ok := collection.ParseGitHubRepo("https://github.com/acme/demo")
			Expect(ok).To(BeTrue())
			Expect(owner).To(Equal("acme"))
			Expect(repo).To(Equal("demo"))
		})

		It("rejects non-GitHub URLs", func() {
			_, _, ok := collection.ParseGitHubRepo("https://gitlab.com/acme/demo.git")
			Expect(ok).To(BeFalse())
		})
	})

	Describe("FromGitHubRepo", func() {
		It("builds an entry from a GitHub repository", func() {
			repo := &github.Repository{
				Name:        "spark-cli",
				HTMLURL:     "https://github.com/variableway/spark-cli",
				Private:     false,
				Description: "Daily CLI tool",
				Language:    "Go",
				Homepage:    "https://variableway.github.io/spark-cli/",
				CreatedAt:   "2026-10-22T00:00:00Z",
				Topics:      []string{"cli", "go"},
			}
			repo.Owner.Login = "variableway"

			entry := collection.FromGitHubRepo(repo, "spark-cli")
			Expect(entry.Name).To(Equal("spark-cli"))
			Expect(entry.Repo).To(Equal("variableway/spark-cli"))
			Expect(entry.URL).To(Equal("https://variableway.github.io/spark-cli/"))
			Expect(entry.Visibility).To(Equal("public"))
			Expect(entry.Language).To(Equal("Go"))
			Expect(entry.Category).To(Equal("app"))
			Expect(entry.Status).To(Equal("maintained"))
			Expect(entry.LocalPath).To(Equal("spark-cli"))
		})

		It("marks private repositories", func() {
			repo := &github.Repository{Name: "secret", HTMLURL: "https://github.com/a/secret", Private: true}
			repo.Owner.Login = "a"
			entry := collection.FromGitHubRepo(repo, "secret")
			Expect(entry.Visibility).To(Equal("private"))
		})

		It("falls back to HTML URL when no homepage", func() {
			repo := &github.Repository{Name: "bare", HTMLURL: "https://github.com/a/bare"}
			repo.Owner.Login = "a"
			entry := collection.FromGitHubRepo(repo, "bare")
			Expect(entry.URL).To(Equal("https://github.com/a/bare"))
		})
	})

	Describe("Scan", func() {
		var tempDir string

		BeforeEach(func() {
			var err error
			tempDir, err = os.MkdirTemp("", "collection-scan")
			Expect(err).NotTo(HaveOccurred())
		})

		AfterEach(func() {
			os.RemoveAll(tempDir)
		})

		It("finds top-level repos only with maxDepth=1", func() {
			writeGitRepo(tempDir, "top", "https://github.com/acme/top.git")
			nested := filepath.Join(tempDir, "parent", "child")
			writeGitRepo(filepath.Join(tempDir, "parent"), "child", "https://github.com/acme/child.git")
			Expect(nested).To(BeADirectory())

			entries, err := collection.Scan(tempDir, true, 1)
			Expect(err).NotTo(HaveOccurred())
			Expect(entries).To(HaveLen(1))
			Expect(entries[0].Name).To(Equal("top"))
		})

		It("finds nested repos with maxDepth=0", func() {
			writeGitRepo(tempDir, "top", "https://github.com/acme/top.git")
			writeGitRepo(filepath.Join(tempDir, "parent"), "child", "https://github.com/acme/child.git")

			entries, err := collection.Scan(tempDir, true, 0)
			Expect(err).NotTo(HaveOccurred())
			Expect(entries).To(HaveLen(2))
		})

		It("builds entries from remote URL when skipAPI is set", func() {
			writeGitRepo(tempDir, "demo", "git@github.com:acme/demo.git")

			entries, err := collection.Scan(tempDir, true, 1)
			Expect(err).NotTo(HaveOccurred())
			Expect(entries).To(HaveLen(1))
			Expect(entries[0].Name).To(Equal("demo"))
			Expect(entries[0].Repo).To(Equal("acme/demo"))
			Expect(entries[0].URL).To(Equal("https://github.com/acme/demo"))
		})

		It("returns empty for directories without git repos", func() {
			entries, err := collection.Scan(tempDir, true, 1)
			Expect(err).NotTo(HaveOccurred())
			Expect(entries).To(BeEmpty())
		})
	})

	Describe("Merge", func() {
		It("preserves curated fields from existing entries", func() {
			existing := []collection.Entry{{
				Name: "demo", Title: "Curated Title", Repo: "acme/demo",
				Category: "reference", Status: "experimental",
				URL: "https://custom.example.com", Description: "curated desc",
			}}
			discovered := []collection.Entry{{
				Name: "demo", Title: "Auto Title", Repo: "acme/demo",
				Category: "app", Status: "maintained",
				URL: "https://github.com/acme/demo", Description: "auto desc",
				Language: "Go", Visibility: "public",
			}}

			merged := collection.Merge(existing, discovered)
			Expect(merged).To(HaveLen(1))
			Expect(merged[0].Title).To(Equal("Curated Title"))
			Expect(merged[0].Category).To(Equal("reference"))
			Expect(merged[0].Status).To(Equal("experimental"))
			Expect(merged[0].URL).To(Equal("https://custom.example.com"))
			Expect(merged[0].Description).To(Equal("curated desc"))
			Expect(merged[0].Language).To(Equal("Go"))
		})

		It("keeps existing entries not found in the scan", func() {
			existing := []collection.Entry{
				{Name: "base-fw", Repo: "acme/base-fw", Category: "base", Status: "maintained"},
			}
			discovered := []collection.Entry{
				{Name: "new-app", Repo: "acme/new-app", Category: "app", Status: "maintained"},
			}

			merged := collection.Merge(existing, discovered)
			Expect(merged).To(HaveLen(2))
			names := []string{merged[0].Name, merged[1].Name}
			Expect(names).To(ContainElement("base-fw"))
			Expect(names).To(ContainElement("new-app"))
		})

		It("appends new discoveries", func() {
			existing := []collection.Entry{{Name: "old", Repo: "a/old", Category: "app", Status: "maintained"}}
			discovered := []collection.Entry{
				{Name: "old", Repo: "a/old", Category: "app", Status: "maintained"},
				{Name: "fresh", Repo: "a/fresh", Category: "app", Status: "maintained"},
			}

			merged := collection.Merge(existing, discovered)
			Expect(merged).To(HaveLen(2))
			Expect(merged[1].Name).To(Equal("fresh"))
		})

		It("matches by repo when names differ", func() {
			existing := []collection.Entry{{Name: "renamed", Repo: "acme/demo", Title: "Keep Me"}}
			discovered := []collection.Entry{{Name: "demo", Repo: "acme/demo", Title: "Auto"}}

			merged := collection.Merge(existing, discovered)
			Expect(merged).To(HaveLen(1))
			Expect(merged[0].Name).To(Equal("demo"))
			Expect(merged[0].Title).To(Equal("Keep Me"))
		})
	})

	Describe("Read and Write", func() {
		var tempDir string

		BeforeEach(func() {
			var err error
			tempDir, err = os.MkdirTemp("", "collection-io")
			Expect(err).NotTo(HaveOccurred())
		})

		AfterEach(func() {
			os.RemoveAll(tempDir)
		})

		It("round-trips registry data through JSON", func() {
			path := filepath.Join(tempDir, "apps.json")
			reg := &collection.Registry{
				Collections: []collection.Entry{
					{Name: "demo", Repo: "acme/demo", Category: "app", Status: "maintained", Visibility: "public"},
				},
			}
			Expect(collection.Write(path, reg)).To(Succeed())

			loaded, err := collection.Read(path)
			Expect(err).NotTo(HaveOccurred())
			Expect(loaded.Version).To(Equal(1))
			Expect(loaded.Schema).To(Equal("./schema.json"))
			Expect(loaded.Collections).To(HaveLen(1))
			Expect(loaded.Collections[0].Name).To(Equal("demo"))
		})

		It("returns empty registry for missing files", func() {
			reg, err := collection.Read(filepath.Join(tempDir, "missing.json"))
			Expect(err).NotTo(HaveOccurred())
			Expect(reg.Collections).To(BeEmpty())
		})

		It("writes valid JSON with required fields", func() {
			path := filepath.Join(tempDir, "out.json")
			reg := &collection.Registry{Collections: []collection.Entry{}}
			Expect(collection.Write(path, reg)).To(Succeed())

			var raw map[string]any
			data, err := os.ReadFile(path)
			Expect(err).NotTo(HaveOccurred())
			Expect(json.Unmarshal(data, &raw)).To(Succeed())
			Expect(raw).To(HaveKey("version"))
			Expect(raw).To(HaveKey("updated_at"))
			Expect(raw).To(HaveKey("collections"))
		})
	})
})
