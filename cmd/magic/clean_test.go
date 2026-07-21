package magic

import (
	"os"
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("Clean", func() {
	var (
		root string
	)

	BeforeEach(func() {
		root = GinkgoT().TempDir()
	})

	Describe("cleanPaths", func() {
		Context("in node mode", func() {
			BeforeEach(func() {
				Expect(os.MkdirAll(filepath.Join(root, "project", "node_modules"), 0o755)).To(Succeed())
				Expect(os.WriteFile(filepath.Join(root, "project", "package-lock.json"), []byte("{}"), 0o644)).To(Succeed())
				Expect(os.MkdirAll(filepath.Join(root, "project", ".venv"), 0o755)).To(Succeed())
			})

			It("removes node_modules dirs and package-lock.json files, leaving .venv untouched", func() {
				cleaned, errs := cleanPaths([]string{root}, true, false)
				Expect(errs).To(BeEmpty())
				Expect(cleaned).To(ConsistOf(
					filepath.Join(root, "project", "node_modules"),
					filepath.Join(root, "project", "package-lock.json"),
				))

				_, err := os.Stat(filepath.Join(root, "project", "node_modules"))
				Expect(os.IsNotExist(err)).To(BeTrue())
				_, err = os.Stat(filepath.Join(root, "project", "package-lock.json"))
				Expect(os.IsNotExist(err)).To(BeTrue())

				_, err = os.Stat(filepath.Join(root, "project", ".venv"))
				Expect(err).NotTo(HaveOccurred())
			})
		})

		Context("in python mode", func() {
			BeforeEach(func() {
				Expect(os.MkdirAll(filepath.Join(root, "project", "node_modules"), 0o755)).To(Succeed())
				Expect(os.WriteFile(filepath.Join(root, "project", "package-lock.json"), []byte("{}"), 0o644)).To(Succeed())
				Expect(os.MkdirAll(filepath.Join(root, "project", ".venv"), 0o755)).To(Succeed())
			})

			It("removes only .venv, leaving node artifacts untouched", func() {
				cleaned, errs := cleanPaths([]string{root}, false, true)
				Expect(errs).To(BeEmpty())
				Expect(cleaned).To(ConsistOf(filepath.Join(root, "project", ".venv")))

				_, err := os.Stat(filepath.Join(root, "project", "node_modules"))
				Expect(err).NotTo(HaveOccurred())
				_, err = os.Stat(filepath.Join(root, "project", "package-lock.json"))
				Expect(err).NotTo(HaveOccurred())
				_, err = os.Stat(filepath.Join(root, "project", ".venv"))
				Expect(os.IsNotExist(err)).To(BeTrue())
			})
		})

		Context("in both mode (default)", func() {
			BeforeEach(func() {
				Expect(os.MkdirAll(filepath.Join(root, "project", "node_modules"), 0o755)).To(Succeed())
				Expect(os.WriteFile(filepath.Join(root, "project", "package-lock.json"), []byte("{}"), 0o644)).To(Succeed())
				Expect(os.MkdirAll(filepath.Join(root, "project", ".venv"), 0o755)).To(Succeed())
			})

			It("removes node_modules, package-lock.json and .venv", func() {
				cleaned, errs := cleanPaths([]string{root}, true, true)
				Expect(errs).To(BeEmpty())
				Expect(cleaned).To(ConsistOf(
					filepath.Join(root, "project", "node_modules"),
					filepath.Join(root, "project", "package-lock.json"),
					filepath.Join(root, "project", ".venv"),
				))
			})
		})

		Context("with a .git directory", func() {
			BeforeEach(func() {
				Expect(os.MkdirAll(filepath.Join(root, ".git", "node_modules"), 0o755)).To(Succeed())
				Expect(os.WriteFile(filepath.Join(root, ".git", "package-lock.json"), []byte("{}"), 0o644)).To(Succeed())
				Expect(os.MkdirAll(filepath.Join(root, "node_modules"), 0o755)).To(Succeed())
			})

			It("skips everything inside .git but cleans the project root", func() {
				cleaned, errs := cleanPaths([]string{root}, true, false)
				Expect(errs).To(BeEmpty())
				Expect(cleaned).To(ConsistOf(filepath.Join(root, "node_modules")))

				_, err := os.Stat(filepath.Join(root, ".git", "node_modules"))
				Expect(err).NotTo(HaveOccurred())
				_, err = os.Stat(filepath.Join(root, ".git", "package-lock.json"))
				Expect(err).NotTo(HaveOccurred())
			})
		})

		Context("with nothing to clean", func() {
			It("returns empty results", func() {
				cleaned, errs := cleanPaths([]string{root}, true, true)
				Expect(errs).To(BeEmpty())
				Expect(cleaned).To(BeEmpty())
			})
		})
	})
})
