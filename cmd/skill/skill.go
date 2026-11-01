package skill

import (
	"github.com/spf13/cobra"
)

var SkillCmd = &cobra.Command{
	Use:   "skill",
	Short: "Discover and manage AI agent skills",
	Long: `Skill management commands for finding and syncing agent skills.

Skills are SKILL.md directories discovered from well-known locations:
  - .mimocode/skills/ and .agents/skills/ in the current project
  - ~/.claude/skills/, ~/.agents/skills/, ~/.mimocode/skills/
  - ~/.local/share/mimocode/builtin_skills/<version>/skills/

Examples:
  spark skill list                 # List all discovered skills
  spark skill sync ./skills        # Copy all skills to ./skills
  spark skill sync ./skills --clear  # Clear target, then copy all skills`,
}

func init() {
	SkillCmd.AddCommand(listCmd)
	SkillCmd.AddCommand(syncCmd)
}
