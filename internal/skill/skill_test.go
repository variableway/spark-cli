package skill_test

import (
	"os"
	"path/filepath"

	"spark/internal/skill"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

func writeSkill(dir, name, frontmatter string) string {
	skillDir := filepath.Join(dir, name)
	Expect(os.MkdirAll(skillDir, 0755)).To(Succeed())
	content := frontmatter + "\n# " + name + "\n"
	Expect(os.WriteFile(filepath.Join(skillDir, "SKILL.md"), []byte(content), 0644)).To(Succeed())
	return skillDir
}

var _ = Describe("Skill", func() {
	var home, cwd string

	BeforeEach(func() {
		var err error
		home, err = os.MkdirTemp("", "skill-home")
		Expect(err).NotTo(HaveOccurred())
		cwd, err = os.MkdirTemp("", "skill-cwd")
		Expect(err).NotTo(HaveOccurred())
		Expect(os.Setenv("HOME", home)).To(Succeed())
	})

	AfterEach(func() {
		os.RemoveAll(home)
		os.RemoveAll(cwd)
	})

	Describe("Discover", func() {
		It("finds skills in project .mimocode/skills", func() {
			writeSkill(filepath.Join(cwd, ".mimocode", "skills"), "alpha",
				"---\nname: alpha\ndescription: test alpha\n---")

			skills, err := skill.Discover(cwd)
			Expect(err).NotTo(HaveOccurred())
			Expect(skills).To(HaveLen(1))
			Expect(skills[0].Name).To(Equal("alpha"))
			Expect(skills[0].Description).To(Equal("test alpha"))
			Expect(skills[0].Source).To(Equal("project"))
		})

		It("finds skills in project .agents/skills", func() {
			writeSkill(filepath.Join(cwd, ".agents", "skills"), "beta",
				"---\nname: beta\ndescription: test beta\n---")

			skills, err := skill.Discover(cwd)
			Expect(err).NotTo(HaveOccurred())
			Expect(skills).To(HaveLen(1))
			Expect(skills[0].Name).To(Equal("beta"))
			Expect(skills[0].Source).To(Equal("project"))
		})

		It("finds skills in global .claude/skills", func() {
			writeSkill(filepath.Join(home, ".claude", "skills"), "gamma",
				"---\nname: gamma\ndescription: test gamma\n---")

			skills, err := skill.Discover(cwd)
			Expect(err).NotTo(HaveOccurred())
			Expect(skills).To(HaveLen(1))
			Expect(skills[0].Name).To(Equal("gamma"))
			Expect(skills[0].Source).To(Equal("claude"))
		})

		It("finds skills in builtin_skills versions", func() {
			builtinDir := filepath.Join(home, ".local", "share", "mimocode", "builtin_skills", "0.1.0", "skills")
			writeSkill(builtinDir, "delta", "---\nname: delta\ndescription: builtin delta\n---")

			skills, err := skill.Discover(cwd)
			Expect(err).NotTo(HaveOccurred())
			Expect(skills).To(HaveLen(1))
			Expect(skills[0].Name).To(Equal("delta"))
			Expect(skills[0].Source).To(Equal("builtin:0.1.0"))
		})

		It("deduplicates skills by name, preferring project over global", func() {
			writeSkill(filepath.Join(cwd, ".mimocode", "skills"), "dup",
				"---\nname: dup\ndescription: project version\n---")
			writeSkill(filepath.Join(home, ".claude", "skills"), "dup",
				"---\nname: dup\ndescription: claude version\n---")

			skills, err := skill.Discover(cwd)
			Expect(err).NotTo(HaveOccurred())
			Expect(skills).To(HaveLen(1))
			Expect(skills[0].Description).To(Equal("project version"))
			Expect(skills[0].Source).To(Equal("project"))
		})

		It("uses directory name when SKILL.md has no frontmatter", func() {
			writeSkill(filepath.Join(cwd, ".mimocode", "skills"), "bare", "# bare skill")

			skills, err := skill.Discover(cwd)
			Expect(err).NotTo(HaveOccurred())
			Expect(skills).To(HaveLen(1))
			Expect(skills[0].Name).To(Equal("bare"))
			Expect(skills[0].Description).To(BeEmpty())
		})

		It("returns empty when no skills exist", func() {
			skills, err := skill.Discover(cwd)
			Expect(err).NotTo(HaveOccurred())
			Expect(skills).To(BeEmpty())
		})
	})

	Describe("Sync", func() {
		It("copies skills to the target directory", func() {
			srcDir := filepath.Join(cwd, ".mimocode", "skills")
			writeSkill(srcDir, "one", "---\nname: one\ndescription: first\n---")
			writeSkill(srcDir, "two", "---\nname: two\ndescription: second\n---")

			skills, err := skill.Discover(cwd)
			Expect(err).NotTo(HaveOccurred())
			Expect(skills).To(HaveLen(2))

			target := filepath.Join(home, "out")
			copied, err := skill.Sync(skills, target, false)
			Expect(err).NotTo(HaveOccurred())
			Expect(copied).To(HaveLen(2))

			Expect(filepath.Join(target, "one", "SKILL.md")).To(BeAnExistingFile())
			Expect(filepath.Join(target, "two", "SKILL.md")).To(BeAnExistingFile())
		})

		It("clears the target directory when requested", func() {
			srcDir := filepath.Join(cwd, ".mimocode", "skills")
			writeSkill(srcDir, "fresh", "---\nname: fresh\n---")

			target := filepath.Join(home, "out")
			Expect(os.MkdirAll(target, 0755)).To(Succeed())
			Expect(os.WriteFile(filepath.Join(target, "stale.txt"), []byte("old"), 0644)).To(Succeed())

			skills, err := skill.Discover(cwd)
			Expect(err).NotTo(HaveOccurred())

			_, err = skill.Sync(skills, target, true)
			Expect(err).NotTo(HaveOccurred())

			Expect(filepath.Join(target, "stale.txt")).NotTo(BeAnExistingFile())
			Expect(filepath.Join(target, "fresh", "SKILL.md")).To(BeAnExistingFile())
		})

		It("creates the target directory when missing", func() {
			srcDir := filepath.Join(cwd, ".mimocode", "skills")
			writeSkill(srcDir, "solo", "---\nname: solo\n---")

			skills, err := skill.Discover(cwd)
			Expect(err).NotTo(HaveOccurred())

			target := filepath.Join(home, "new-dir")
			_, err = skill.Sync(skills, target, false)
			Expect(err).NotTo(HaveOccurred())
			Expect(filepath.Join(target, "solo", "SKILL.md")).To(BeAnExistingFile())
		})
	})
})
