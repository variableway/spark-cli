package task_test

import (
	"spark/internal/task"
	"os"
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("Task", func() {
	Describe("copyMarkdownFiles", func() {
		var (
			srcDir string
			dstDir string
		)

		BeforeEach(func() {
			srcDir, _ = os.MkdirTemp("", "task-src-*")
			dstDir, _ = os.MkdirTemp("", "task-dst-*")
		})

		AfterEach(func() {
			os.RemoveAll(srcDir)
			os.RemoveAll(dstDir)
		})

		Context("when source has mixed file types", func() {
			BeforeEach(func() {
				os.WriteFile(filepath.Join(srcDir, "README.md"), []byte("# README"), 0644)
				os.WriteFile(filepath.Join(srcDir, "specs.md"), []byte("# Specs"), 0644)
				os.WriteFile(filepath.Join(srcDir, "notes.txt"), []byte("Notes"), 0644)
				os.WriteFile(filepath.Join(srcDir, "config.yaml"), []byte("key: value"), 0644)

				subDir := filepath.Join(srcDir, "subdir")
				os.MkdirAll(subDir, 0755)
				os.WriteFile(filepath.Join(subDir, "nested.md"), []byte("# Nested"), 0644)
				os.WriteFile(filepath.Join(subDir, "data.json"), []byte("{}"), 0644)
			})

			It("should only copy .md files and preserve directory structure", func() {
				err := task.CopyMarkdownFiles(srcDir, dstDir)
				Expect(err).NotTo(HaveOccurred())

				Expect(filepath.Join(dstDir, "README.md")).To(BeARegularFile())
				Expect(filepath.Join(dstDir, "specs.md")).To(BeARegularFile())
				Expect(filepath.Join(dstDir, "subdir", "nested.md")).To(BeARegularFile())

				Expect(filepath.Join(dstDir, "notes.txt")).NotTo(BeAnExistingFile())
				Expect(filepath.Join(dstDir, "config.yaml")).NotTo(BeAnExistingFile())
				Expect(filepath.Join(dstDir, "subdir", "data.json")).NotTo(BeAnExistingFile())
			})

			It("should preserve file contents", func() {
				err := task.CopyMarkdownFiles(srcDir, dstDir)
				Expect(err).NotTo(HaveOccurred())

				content, err := os.ReadFile(filepath.Join(dstDir, "README.md"))
				Expect(err).NotTo(HaveOccurred())
				Expect(string(content)).To(Equal("# README"))

				content, err = os.ReadFile(filepath.Join(dstDir, "subdir", "nested.md"))
				Expect(err).NotTo(HaveOccurred())
				Expect(string(content)).To(Equal("# Nested"))
			})
		})

		Context("when source has no markdown files", func() {
			BeforeEach(func() {
				os.WriteFile(filepath.Join(srcDir, "notes.txt"), []byte("Notes"), 0644)
				os.WriteFile(filepath.Join(srcDir, "config.yaml"), []byte("key: value"), 0644)
			})

			It("should not copy any files", func() {
				err := task.CopyMarkdownFiles(srcDir, dstDir)
				Expect(err).NotTo(HaveOccurred())

				entries, _ := os.ReadDir(dstDir)
				Expect(len(entries)).To(BeZero())
			})
		})

		Context("when source directory does not exist", func() {
			It("should return an error", func() {
				err := task.CopyMarkdownFiles("/nonexistent/path", dstDir)
				Expect(err).To(HaveOccurred())
			})
		})
	})
})
