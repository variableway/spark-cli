package git_test

import (
	"monolize/internal/git"
	"os"
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("Finder", func() {
	var tempDir string

	BeforeEach(func() {
		var err error
		tempDir, err = os.MkdirTemp("", "git-finder-test")
		Expect(err).NotTo(HaveOccurred())
	})

	AfterEach(func() {
		os.RemoveAll(tempDir)
	})

	Describe("IsGitRepository", func() {
		It("should return true for a directory containing a .git folder", func() {
			repoPath := filepath.Join(tempDir, "repo1")
			err := os.MkdirAll(filepath.Join(repoPath, ".git"), 0755)
			Expect(err).NotTo(HaveOccurred())

			Expect(git.IsGitRepository(repoPath)).To(BeTrue())
		})

		It("should return false for a directory without a .git folder", func() {
			repoPath := filepath.Join(tempDir, "not-a-repo")
			err := os.MkdirAll(repoPath, 0755)
			Expect(err).NotTo(HaveOccurred())

			Expect(git.IsGitRepository(repoPath)).To(BeFalse())
		})

		It("should return false for a non-existent directory", func() {
			Expect(git.IsGitRepository("/non/existent/path")).To(BeFalse())
		})
	})

	Describe("FindRepositories", func() {
		It("should return the path itself if the path is a git repository", func() {
			repoPath := filepath.Join(tempDir, "single-repo")
			err := os.MkdirAll(filepath.Join(repoPath, ".git"), 0755)
			Expect(err).NotTo(HaveOccurred())

			found, err := git.FindRepositories(repoPath)
			Expect(err).NotTo(HaveOccurred())
			Expect(found).To(HaveLen(1))
			Expect(found[0]).To(ContainSubstring("single-repo"))
		})

		It("should find all git repositories in a directory", func() {
			// Create some repositories
			repos := []string{"repo1", "repo2"}
			for _, r := range repos {
				repoPath := filepath.Join(tempDir, r)
				err := os.MkdirAll(filepath.Join(repoPath, ".git"), 0755)
				Expect(err).NotTo(HaveOccurred())
			}

			// Create a non-repository directory
			err := os.MkdirAll(filepath.Join(tempDir, "not-a-repo"), 0755)
			Expect(err).NotTo(HaveOccurred())

			found, err := git.FindRepositories(tempDir)
			Expect(err).NotTo(HaveOccurred())
			Expect(found).To(HaveLen(2))

			var foundNames []string
			for _, f := range found {
				foundNames = append(foundNames, filepath.Base(f))
			}
			Expect(foundNames).To(ContainElements("repo1", "repo2"))
		})

		It("should return an empty list if no repositories are found", func() {
			found, err := git.FindRepositories(tempDir)
			Expect(err).NotTo(HaveOccurred())
			Expect(found).To(BeEmpty())
		})

		It("should return an error if the path does not exist", func() {
			_, err := git.FindRepositories("/non/existent/path")
			Expect(err).To(HaveOccurred())
		})
	})
})
