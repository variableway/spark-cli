package registry_test

import (
	"os"
	"path/filepath"
	"strings"

	"spark/internal/registry"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

func mkdirAll(parts ...string) {
	Expect(os.MkdirAll(filepath.Join(parts...), 0755)).To(Succeed())
}

var _ = Describe("Categorize", func() {
	var tempDir string

	BeforeEach(func() {
		var err error
		tempDir, err = os.MkdirTemp("", "registry-categorize")
		Expect(err).NotTo(HaveOccurred())
	})

	AfterEach(func() {
		os.RemoveAll(tempDir)
	})

	It("groups projects by category/subcategory and defaults to others", func() {
		// three real categories on disk; only skills has subcategories for now
		mkdirAll(tempDir, "skills", "agent")
		mkdirAll(tempDir, "skills", "ui-ux")
		mkdirAll(tempDir, "products")
		mkdirAll(tempDir, "plugins")

		projects := []registry.Project{
			{Name: "taste-skill", Repo: "https://github.com/a/taste.git", Path: "skills/ui-ux/taste-skill"},
			{Name: "agency", Repo: "https://github.com/b/agency.git", Path: "skills/agent/agency"},
			{Name: "legacy", Repo: "https://github.com/c/legacy.git", Path: "skills/legacy"}, // no subcategory
			{Name: "stray", Repo: "https://github.com/d/stray.git", Path: "stray"},           // no category
		}

		groups, skipped, err := registry.Categorize(tempDir, projects)
		Expect(err).NotTo(HaveOccurred())

		Expect(groups).To(HaveLen(3))
		Expect([]string{groups[0].Name, groups[1].Name, groups[2].Name}).
			To(Equal([]string{"plugins", "products", "skills"}))

		find := func(cat string, sub string) []string {
			for _, c := range groups {
				if c.Name != cat {
					continue
				}
				for _, s := range c.Subcategories {
					if s.Name == sub {
						var names []string
						for _, p := range s.Projects {
							names = append(names, p.Name)
						}
						return names
					}
				}
			}
			return nil
		}
		subNames := func(cat string) []string {
			for _, c := range groups {
				if c.Name == cat {
					var out []string
					for _, s := range c.Subcategories {
						out = append(out, s.Name)
					}
					return out
				}
			}
			return nil
		}

		Expect(find("skills", "agent")).To(Equal([]string{"agency"}))
		Expect(find("skills", "ui-ux")).To(Equal([]string{"taste-skill"}))
		// project without a subcategory lands in others, path unchanged
		Expect(find("skills", "others")).To(Equal([]string{"legacy"}))
		// every category gets an others bucket, even with no project in it,
		// and it is always sorted last inside its category
		Expect(subNames("skills")).To(Equal([]string{"agent", "ui-ux", "others"}))
		Expect(subNames("products")).To(Equal([]string{"others"}))
		Expect(subNames("plugins")).To(Equal([]string{"others"}))
		// root-level project has no category: skipped for the caller to warn
		Expect(skipped).To(HaveLen(1))
		Expect(skipped[0].Name).To(Equal("stray"))
	})

	It("keeps nested projects under their first two segments with full path", func() {
		mkdirAll(tempDir, "skills", "dev-tool")
		projects := []registry.Project{
			{Name: "fire-skills", Repo: "https://github.com/x/fire.git", Path: "skills/dev-tool/fire-skills"},
			{Name: "01-superpowers", Repo: "https://github.com/y/super.git", Path: "skills/dev-tool/fire-skills/downloads/01-superpowers"},
		}

		groups, skipped, err := registry.Categorize(tempDir, projects)
		Expect(err).NotTo(HaveOccurred())
		Expect(skipped).To(BeEmpty())
		Expect(groups).To(HaveLen(1))
		Expect(groups[0].Name).To(Equal("skills"))
		Expect(groups[0].Subcategories).To(HaveLen(2)) // dev-tool + others

		var dev *registry.Subcategory
		for i := range groups[0].Subcategories {
			if groups[0].Subcategories[i].Name == "dev-tool" {
				dev = &groups[0].Subcategories[i]
			}
		}
		Expect(dev).NotTo(BeNil())
		Expect(dev.Projects).To(HaveLen(2))
		// parent before its nested clone (path order)
		Expect(dev.Projects[0].Path).To(Equal("skills/dev-tool/fire-skills"))
		Expect(dev.Projects[1].Path).To(Equal("skills/dev-tool/fire-skills/downloads/01-superpowers"))
	})

	It("returns no groups for a folder without category directories", func() {
		projects := []registry.Project{
			{Name: "flat", Repo: "https://github.com/e/flat.git", Path: "flat"},
		}
		groups, skipped, err := registry.Categorize(tempDir, projects)
		Expect(err).NotTo(HaveOccurred())
		Expect(groups).To(BeNil())
		// every project is reported unclassified so the caller keeps the legacy format
		Expect(skipped).To(HaveLen(1))
	})

	It("does not treat git repositories as category or subcategory directories", func() {
		mkdirAll(tempDir, "skills", "agent")
		// a repo in the folder root must NOT become a category
		writeGitRepo(tempDir, "rootproj", "https://github.com/f/rootproj.git")
		// a repo directly under a category must NOT become a subcategory
		writeGitRepo(filepath.Join(tempDir, "skills"), "legacyproj", "https://github.com/g/legacyproj.git")

		projects := []registry.Project{
			{Name: "rootproj", Repo: "https://github.com/f/rootproj.git", Path: "rootproj"},
			{Name: "legacyproj", Repo: "https://github.com/g/legacyproj.git", Path: "skills/legacyproj"},
			{Name: "agent-repo", Repo: "https://github.com/h/agent.git", Path: "skills/agent/agent-repo"},
		}

		groups, skipped, err := registry.Categorize(tempDir, projects)
		Expect(err).NotTo(HaveOccurred())
		// only skills (the non-repo dir) is a category
		Expect(groups).To(HaveLen(1))
		Expect(groups[0].Name).To(Equal("skills"))
		Expect(groups[0].Subcategories).To(HaveLen(2)) // agent + others (legacyproj is not a subcategory)
		var subNames []string
		for _, s := range groups[0].Subcategories {
			subNames = append(subNames, s.Name)
		}
		Expect(subNames).To(Equal([]string{"agent", "others"}))

		// the root-level repo has no category: skipped for a warning
		Expect(skipped).To(HaveLen(1))
		Expect(skipped[0].Name).To(Equal("rootproj"))
	})
})

var _ = Describe("Categorized registry format", func() {
	var tempDir string

	BeforeEach(func() {
		var err error
		tempDir, err = os.MkdirTemp("", "registry-v2")
		Expect(err).NotTo(HaveOccurred())
	})

	AfterEach(func() {
		os.RemoveAll(tempDir)
	})

	categorized := func() *registry.Registry {
		return &registry.Registry{Categories: []registry.Category{
			{Name: "skills", Subcategories: []registry.Subcategory{
				{Name: "agent", Projects: []registry.Project{
					{Name: "agency", Repo: "https://github.com/b/agency.git", Path: "skills/agent/agency", Desc: "keep me"},
				}},
				{Name: "others", Projects: []registry.Project{}},
			}},
			{Name: "products", Subcategories: []registry.Subcategory{
				{Name: "others", Projects: []registry.Project{}},
			}},
		}}
	}

	It("writes version 2 with categories and no top-level projects", func() {
		path := filepath.Join(tempDir, "registry_refs.yaml")
		Expect(registry.Write(path, categorized())).To(Succeed())

		data, err := os.ReadFile(path)
		Expect(err).NotTo(HaveOccurred())
		text := string(data)
		Expect(text).To(ContainSubstring("version: 2"))
		Expect(text).To(ContainSubstring("categories:"))
		Expect(text).To(ContainSubstring("name: products"))
		// no legacy top-level projects key (nested subcategory keys are fine)
		Expect(text).ToNot(MatchRegexp("(?m)^projects:"))
		// subcategory order keeps others last inside its category
		Expect(strings.Index(text, "name: agent")).To(BeNumerically("<", strings.Index(text, "name: others")))
	})

	It("reads back flattened projects for legacy callers", func() {
		path := filepath.Join(tempDir, "registry_refs2.yaml")
		Expect(registry.Write(path, categorized())).To(Succeed())

		got, err := registry.Read(path)
		Expect(err).NotTo(HaveOccurred())
		Expect(got.IsCategorized()).To(BeTrue())
		Expect(got.Version).To(Equal(registry.RegistryVersion))
		Expect(got.AllProjects()).To(HaveLen(1))
		Expect(got.Projects).To(HaveLen(1)) // derived flat view
		Expect(got.Projects[0].Path).To(Equal("skills/agent/agency"))

		p, err := registry.FindByName(got, "agency")
		Expect(err).NotTo(HaveOccurred())
		Expect(p.Desc).To(Equal("keep me"))
	})

	It("writes the JSON mirror in the categorized shape", func() {
		path := filepath.Join(tempDir, "registry_refs.json")
		Expect(registry.WriteJSON(path, categorized())).To(Succeed())

		data, err := os.ReadFile(path)
		Expect(err).NotTo(HaveOccurred())
		text := string(data)
		Expect(text).To(ContainSubstring(`"version": 2`))
		Expect(text).To(ContainSubstring(`"categories"`))
		// no legacy top-level "projects" key (nested subcategory keys are fine)
		Expect(text).ToNot(MatchRegexp(`(?m)^  "projects":`))
	})

	It("keeps the legacy flat shape for flat registries", func() {
		path := filepath.Join(tempDir, "registry_legacy.yaml")
		flat := &registry.Registry{Projects: []registry.Project{
			{Name: "spark-cli", Repo: "https://github.com/variableway/spark-cli.git", Path: "spark-cli"},
		}}
		Expect(registry.Write(path, flat)).To(Succeed())

		data, err := os.ReadFile(path)
		Expect(err).NotTo(HaveOccurred())
		Expect(string(data)).To(ContainSubstring("projects:"))
		Expect(string(data)).ToNot(ContainSubstring("version:"))

		got, err := registry.Read(path)
		Expect(err).NotTo(HaveOccurred())
		Expect(got.IsCategorized()).To(BeFalse())
		Expect(got.Projects).To(HaveLen(1))
	})
})
