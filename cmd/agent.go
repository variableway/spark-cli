package cmd

import (
	"fmt"
	"monolize/internal/agent"
	"monolize/internal/tui"
	"strings"

	"github.com/pterm/pterm"
	"github.com/spf13/cobra"
)

var agentUseTUI bool
var agentManager = agent.NewManager()

var agentCmd = &cobra.Command{
	Use:   "agent",
	Short: "AI Agent configuration management",
	Long: `Manage configurations for different AI Agents:
- Claude Code
- OpenAI Codex
- Kimi CLI
- GLM (Zhipu AI)

You can view, edit, and reset configurations for each agent.

Use --tui flag for interactive mode.`,
}

var agentListCmd = &cobra.Command{
	Use:   "list",
	Short: "List all supported AI Agents",
	Long:  `List all supported AI Agents and their configuration file locations.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		agents := agentManager.ListAgents()

		pterm.DefaultHeader.WithFullWidth().Println("Supported AI Agents")
		pterm.Println()

		tableData := pterm.TableData{{"Agent", "Display Name", "Config Files", "Status"}}
		for _, a := range agents {
			exists := agentManager.ConfigExists(a.Name)
			status := "❌ Not configured"
			for _, e := range exists {
				if e {
					status = "✅ Configured"
					break
				}
			}

			configFiles := strings.Join(a.ConfigFiles, "\n")
			tableData = append(tableData, []string{
				string(a.Name),
				a.DisplayName,
				configFiles,
				status,
			})
		}

		pterm.DefaultTable.WithHasHeader().WithData(tableData).Render()
		return nil
	},
}

var agentViewCmd = &cobra.Command{
	Use:   "view <agent>",
	Short: "View configuration for an AI Agent",
	Long: `View the configuration files for a specific AI Agent.

Available agents: claude-code, codex, kimi, glm

Example:
  monolize agent view claude-code
  monolize agent view kimi`,
	Args: cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		agentType := agent.AgentType(args[0])

		configs, err := agentManager.ViewConfig(agentType)
		if err != nil {
			return err
		}

		info, _ := agentManager.GetAgentInfo(agentType)
		pterm.DefaultHeader.WithFullWidth().Println(fmt.Sprintf("%s Configuration", info.DisplayName))
		pterm.Println()

		for path, content := range configs {
			pterm.DefaultSection.Printf("File: %s", path)
			pterm.Println()
			pterm.Println(content)
			pterm.Println()
		}

		return nil
	},
}

var agentEditCmd = &cobra.Command{
	Use:   "edit <agent> [config-index]",
	Short: "Edit configuration for an AI Agent",
	Long: `Edit the configuration files for a specific AI Agent using your default editor.

The editor is determined by $EDITOR environment variable.
On Windows, defaults to notepad if $EDITOR is not set.
On Unix, defaults to vim if $EDITOR is not set.

Available agents: claude-code, codex, kimi, glm

Example:
  monolize agent edit claude-code
  monolize agent edit kimi 0`,
	Args: cobra.RangeArgs(1, 2),
	RunE: func(cmd *cobra.Command, args []string) error {
		agentType := agent.AgentType(args[0])

		configIndex := 0
		if len(args) > 1 {
			_, err := fmt.Sscanf(args[1], "%d", &configIndex)
			if err != nil {
				return fmt.Errorf("invalid config index: %s", args[1])
			}
		}

		paths, err := agentManager.GetAgentConfigPath(agentType)
		if err != nil {
			return err
		}

		if agentUseTUI {
			selected, err := tui.SelectItem("Select config file to edit:", paths)
			if err != nil {
				pterm.Info.Println("Edit cancelled.")
				return nil
			}
			for i, p := range paths {
				if p == selected {
					configIndex = i
					break
				}
			}
		}

		info, _ := agentManager.GetAgentInfo(agentType)
		pterm.Info.Printf("Opening %s config file: %s\n", info.DisplayName, paths[configIndex])

		return agentManager.EditConfig(agentType, configIndex)
	},
}

var agentResetCmd = &cobra.Command{
	Use:   "reset <agent>",
	Short: "Reset configuration for an AI Agent",
	Long: `Reset the configuration files for a specific AI Agent.
This will backup existing config files with .bak extension.

Available agents: claude-code, codex, kimi, glm

Example:
  monolize agent reset claude-code
  monolize agent reset kimi`,
	Args: cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		agentType := agent.AgentType(args[0])

		info, _ := agentManager.GetAgentInfo(agentType)

		confirmed := false
		if agentUseTUI {
			var err error
			confirmed, err = tui.Confirm(fmt.Sprintf("Reset %s configuration? (Files will be backed up)", info.DisplayName))
			if err != nil {
				pterm.Info.Println("Reset cancelled.")
				return nil
			}
		} else {
			pterm.Warning.Printf("This will reset %s configuration. Files will be backed up with .bak extension.\n", info.DisplayName)
			fmt.Print("Continue? (y/N): ")
			var response string
			fmt.Scanln(&response)
			confirmed = strings.ToLower(response) == "y" || strings.ToLower(response) == "yes"
		}

		if !confirmed {
			pterm.Info.Println("Reset cancelled.")
			return nil
		}

		err := agentManager.ResetConfig(agentType)
		if err != nil {
			return err
		}

		pterm.Success.Printf("%s configuration has been reset. Original files backed up.\n", info.DisplayName)
		return nil
	},
}

func init() {
	agentCmd.PersistentFlags().BoolVar(&agentUseTUI, "tui", false, "Enable interactive TUI mode")

	agentCmd.AddCommand(agentListCmd)
	agentCmd.AddCommand(agentViewCmd)
	agentCmd.AddCommand(agentEditCmd)
	agentCmd.AddCommand(agentResetCmd)

	rootCmd.AddCommand(agentCmd)
}
