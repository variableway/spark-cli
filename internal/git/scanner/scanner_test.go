package scanner_test

import (
	"database/sql"
	"os"
	"path/filepath"

	"spark/internal/git/scanner"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	_ "modernc.org/sqlite"
)

func writeGitRepo(root, name, remoteURL string) string {
	repoPath := filepath.Join(root, name)
	configDir := filepath.Join(repoPath, ".git")
	Expect(os.MkdirAll(configDir, 0755)).To(Succeed())

	config := `[remote "origin"]` + "\n\turl = " + remoteURL + "\n"
	Expect(os.WriteFile(filepath.Join(configDir, "config"), []byte(config), 0644)).To(Succeed())

	return repoPath
}

var _ = Describe("Scanner", func() {
	var tempDir string

	BeforeEach(func() {
		var err error
		tempDir, err = os.MkdirTemp("", "git-scanner-test")
		Expect(err).NotTo(HaveOccurred())
	})

	AfterEach(func() {
		os.RemoveAll(tempDir)
	})

	Describe("Scan", func() {
		It("should find repositories with valid origin remotes", func() {
			writeGitRepo(tempDir, "spark-cli", "https://github.com/variableway/spark-cli.git")
			writeGitRepo(tempDir, "other", "git@github.com:acme/demo.git")

			repos, err := scanner.Scan(tempDir, scanner.Options{SkipAPI: true})
			Expect(err).NotTo(HaveOccurred())
			Expect(repos).To(HaveLen(2))

			byName := map[string]scanner.RepoInfo{}
			for _, repo := range repos {
				byName[repo.Name] = repo
			}

			Expect(byName["spark-cli"].Owner).To(Equal("variableway"))
			Expect(byName["spark-cli"].Repo).To(Equal("spark-cli"))
			Expect(byName["spark-cli"].RepoType).To(Equal("github"))
			Expect(byName["other"].RemoteURL).To(Equal("git@github.com:acme/demo"))
		})

		It("should skip repositories without origin remote", func() {
			repoPath := filepath.Join(tempDir, "local-only")
			Expect(os.MkdirAll(filepath.Join(repoPath, ".git"), 0755)).To(Succeed())

			repos, err := scanner.Scan(tempDir, scanner.Options{SkipAPI: true})
			Expect(err).NotTo(HaveOccurred())
			Expect(repos).To(BeEmpty())
		})
	})

	Describe("Store", func() {
		It("should save and update repositories in sqlite", func() {
			dbPath := filepath.Join(tempDir, "nested", "feeds.db")
			store, err := scanner.OpenStore(dbPath)
			Expect(err).NotTo(HaveOccurred())
			defer store.Close()

			repos := []scanner.RepoInfo{
				{
					Path:      "/tmp/spark-cli",
					Name:      "spark-cli",
					RemoteURL: "https://github.com/variableway/spark-cli",
					RepoType:  "github",
					Owner:     "variableway",
					Repo:      "spark-cli",
					Stars:     10,
				},
			}
			Expect(store.SaveRepos(repos)).To(Succeed())

			repos[0].Stars = 20
			repos[0].Description = "updated"
			Expect(store.SaveRepos(repos)).To(Succeed())

			db, err := sql.Open("sqlite", dbPath)
			Expect(err).NotTo(HaveOccurred())
			defer db.Close()

			var stars int
			var description string
			err = db.QueryRow(`SELECT stars, description FROM repos WHERE path = ?`, "/tmp/spark-cli").Scan(&stars, &description)
			Expect(err).NotTo(HaveOccurred())
			Expect(stars).To(Equal(20))
			Expect(description).To(Equal("updated"))
		})
	})

	Describe("DefaultDBPath", func() {
		It("should point to ~/.innate/feeds.db", func() {
			path, err := scanner.DefaultDBPath()
			Expect(err).NotTo(HaveOccurred())
			Expect(path).To(HaveSuffix(filepath.Join(".innate", "feeds.db")))
		})
	})
})
