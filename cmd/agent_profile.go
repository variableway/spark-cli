package cmd

import (
	"fmt"
	"monolize/internal/agent"
	"monolize/internal/tui"

	"github.com/pterm/pterm"
	"github.com/spf13/cobra"
)

var profileType string
var profileProject string

var agentProfileCmd = &cobra.Command{
	Use:   "profile",
	Short: "Manage AI Agent configuration profiles",
	Long: `Manage profiles (templates) for AI Agents to easily switch configurations between different projects.
For example, you can create a 'claude-opus' profile and a 'glm-4' profile, and apply them to different projects.`,
}

var agentProfileListCmd = &cobra.Command{
	Use:   "list",
	Short: "List all agent profiles",
	RunE: func(cmd *cobra.Command, args []string) error {
		profiles, err := agentManager.ListProfiles()
		if err != nil {
			return err
		}

		if len(profiles) == 0 {
			pterm.Info.Println("No profiles found. Use 'monolize agent profile add' to create one.")
			return nil
		}

		pterm.DefaultHeader.WithFullWidth().Println("Agent Profiles")
		pterm.Println()

		tableData := pterm.TableData{{"Profile Name", "Agent Type", "Location"}}
		for _, p := range profiles {
			tableData = append(tableData, []string{
				p.Name,
				string(p.Meta.Agent),
				p.Dir,
			})
		}

		pterm.DefaultTable.WithHasHeader().WithData(tableData).Render()
		return nil
	},
}

var agentProfileAddCmd = &cobra.Command{
	Use:   "add <name>",
	Short: "Add a new agent profile",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		name := args[0]

		if profileType == "" {
			return fmt.Errorf("agent type is required, use --type (e.g. claude-code, glm)")
		}

		agentType := agent.AgentType(profileType)

		pterm.Info.Printf("Creating profile '%s' for agent '%s'...\n", name, agentType)
		if err := agentManager.AddProfile(name, agentType); err != nil {
			return fmt.Errorf("failed to create profile: %w", err)
		}

		pterm.Success.Printf("Profile '%s' created successfully!\n", name)
		pterm.Info.Printf("Use 'monolize agent profile edit %s' to customize it.\n", name)
		return nil
	},
}

var agentProfileShowCmd = &cobra.Command{
	Use:   "show <name>",
	Short: "Show the configuration of a profile",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		name := args[0]

		configs, err := agentManager.ViewProfileConfig(name)
		if err != nil {
			return err
		}

		pterm.DefaultHeader.WithFullWidth().Println(fmt.Sprintf("Profile: %s", name))
		pterm.Println()

		for path, content := range configs {
			pterm.DefaultSection.Printf("File: %s", path)
			pterm.Println()
			if content == "" {
				pterm.Println("(Empty file)")
			} else {
				pterm.Println(content)
			}
			pterm.Println()
		}

		return nil
	},
}

var agentProfileEditCmd = &cobra.Command{
	Use:   "edit <name> [config-index]",
	Short: "Edit a profile's configuration",
	Args:  cobra.RangeArgs(1, 2),
	RunE: func(cmd *cobra.Command, args []string) error {
		name := args[0]

		configIndex := 0
		if len(args) > 1 {
			_, err := fmt.Sscanf(args[1], "%d", &configIndex)
			if err != nil {
				return fmt.Errorf("invalid config index: %s", args[1])
			}
		}

		profile, err := agentManager.GetProfile(name)
		if err != nil {
			return err
		}

		info, _ := agentManager.GetAgentInfo(profile.Meta.Agent)

		if agentUseTUI {
			selected, err := tui.SelectItem("Select config file to edit:", info.ConfigFiles)
			if err != nil {
				pterm.Info.Println("Edit cancelled.")
				return nil
			}
			for i, p := range info.ConfigFiles {
				if p == selected {
					configIndex = i
					break
				}
			}
		}

		pterm.Info.Printf("Opening profile %s config file: %s\n", name, info.ConfigFiles[configIndex])
		return agentManager.EditProfileConfig(name, configIndex)
	},
}

var agentUseCmd = &cobra.Command{
	Use:   "use <profile-name>",
	Short: "Apply a profile to the current project",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		name := args[0]

		projectDir := profileProject
		if projectDir == "" {
			projectDir = "."
		}

		pterm.Info.Printf("Applying profile '%s' to project at '%s'...\n", name, projectDir)

		if err := agentManager.ApplyProfile(name, projectDir); err != nil {
			return fmt.Errorf("failed to apply profile: %w", err)
		}

		pterm.Success.Println("Profile applied successfully!")
		return nil
	},
}

var agentCurrentCmd = &cobra.Command{
	Use:   "current",
	Short: "Show the current applied profile in the project",
	RunE: func(cmd *cobra.Command, args []string) error {
		projectDir := profileProject
		if projectDir == "" {
			projectDir = "."
		}

		current, err := agentManager.CurrentProfile(projectDir)
		if err != nil {
			return err
		}

		if current == "" {
			pterm.Warning.Println("No agent profile is currently applied to this project.")
			pterm.Info.Println("Use 'monolize agent use <profile-name>' to apply one.")
			return nil
		}

		pterm.Success.Printf("Current profile: %s\n", current)
		return nil
	},
}

func init() {
	agentCmd.AddCommand(agentProfileCmd)
	agentCmd.AddCommand(agentUseCmd)
	agentCmd.AddCommand(agentCurrentCmd)

	agentProfileCmd.AddCommand(agentProfileListCmd)
	agentProfileCmd.AddCommand(agentProfileAddCmd)
	agentProfileCmd.AddCommand(agentProfileShowCmd)
	agentProfileCmd.AddCommand(agentProfileEditCmd)

	agentProfileAddCmd.Flags().StringVarP(&profileType, "type", "t", "", "Agent type (e.g. claude-code, glm)")

	agentUseCmd.Flags().StringVarP(&profileProject, "project", "p", ".", "Project directory path")
	agentCurrentCmd.Flags().StringVarP(&profileProject, "project", "p", ".", "Project directory path")
}
