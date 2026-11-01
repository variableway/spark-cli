package skill

import (
	"encoding/json"
	"fmt"
	"spark/internal/skill"

	"github.com/fatih/color"
	"github.com/spf13/cobra"
)

var jsonOutput bool

var listCmd = &cobra.Command{
	Use:   "list",
	Short: "List all discovered skills",
	Long:  `Scan well-known skill locations and list every skill found.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		skills, err := skill.Discover(".")
		if err != nil {
			return err
		}

		if jsonOutput {
			return printJSON(skills)
		}

		if len(skills) == 0 {
			fmt.Println("No skills found.")
			fmt.Println()
			fmt.Println("Searched locations:")
			fmt.Println("  .mimocode/skills/, .mimocode/skill/, .agents/skills/  (project)")
			fmt.Println("  ~/.claude/skills/, ~/.agents/skills/, ~/.mimocode/skills/")
			fmt.Println("  ~/.local/share/mimocode/builtin_skills/<version>/skills/")
			return nil
		}

		headerColor := color.New(color.FgGreen, color.Bold)
		headerColor.Printf("Found %d skill(s)\n\n", len(skills))

		fmt.Printf("%-24s %-16s %s\n", "NAME", "SOURCE", "PATH")
		fmt.Printf("%-24s %-16s %s\n", "----", "------", "----")
		for _, s := range skills {
			desc := s.Description
			if len(desc) > 60 {
				desc = desc[:57] + "..."
			}
			fmt.Printf("%-24s %-16s %s\n", s.Name, s.Source, s.Path)
			if desc != "" {
				fmt.Printf("%-24s %-16s %s\n", "", "", color.HiBlackString(desc))
			}
		}
		return nil
	},
}

func init() {
	listCmd.Flags().BoolVar(&jsonOutput, "json", false, "Output skills as JSON")
}

func printJSON(skills []skill.Skill) error {
	data, err := json.MarshalIndent(skills, "", "  ")
	if err != nil {
		return err
	}
	fmt.Println(string(data))
	return nil
}
