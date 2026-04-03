package cmd

import (
	"fmt"
	"monolize/internal/task"
	"monolize/internal/tui"

	"github.com/pterm/pterm"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var (
	taskDir     string
	githubOwner string
	workDir     string
	useTUI      bool
)

var taskCmd = &cobra.Command{
	Use:   "task",
	Short: "Task management commands",
	Long: `Manage tasks: dispatch tasks to new directories and sync back changes.

Use --tui flag to enable interactive terminal UI mode with:
- Task selection list (arrow keys to navigate)
- Confirmation dialogs
- Progress spinners`,
}

var taskDispatchCmd = &cobra.Command{
	Use:   "dispatch [task-name]",
	Short: "Dispatch a task to a new working directory",
	Long: `Copy a task from the task directory to a new working directory,
initialize git repository and create a GitHub repository.

In TUI mode, you can interactively select the task to dispatch.

Example:
  spark task dispatch my-task --dest ./workspace/my-task
  spark task dispatch --tui`,
	Args: cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		if taskDir == "" {
			return fmt.Errorf("task directory is required, use --task-dir or set in config")
		}
		if githubOwner == "" {
			return fmt.Errorf("github owner is required, use --owner or set in config")
		}

		taskName := ""
		if len(args) > 0 {
			taskName = args[0]
		}

		if useTUI {
			return runDispatchTUI(taskName)
		}
		return runDispatchCLI(taskName)
	},
}

var taskSyncCmd = &cobra.Command{
	Use:   "sync [task-name]",
	Short: "Sync task changes back to the task directory",
	Long: `Copy the task implementation from working directory back to the original task directory.

In TUI mode, you can interactively select the task to sync.

Example:
  spark task sync my-task --work-path ./workspace/my-task
  spark task sync --tui`,
	Args: cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		if taskDir == "" {
			return fmt.Errorf("task directory is required, use --task-dir or set in config")
		}

		taskName := ""
		if len(args) > 0 {
			taskName = args[0]
		}

		if useTUI {
			return runSyncTUI(taskName)
		}
		return runSyncCLI(taskName)
	},
}

var taskListCmd = &cobra.Command{
	Use:   "list",
	Short: "List all tasks and features",
	Long:  `List all tasks (directories) in the task directory and features in tasks/features.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if taskDir == "" {
			taskDir = "."
		}

		mgr := task.NewManager(taskDir, githubOwner, workDir, false)

		// List task directories
		tasks, err := mgr.ListTasks()
		if err != nil {
			return err
		}

		if len(tasks) > 0 {
			pterm.DefaultSection.Println("Task Directories")
			tableData := pterm.TableData{}
			for i, t := range tasks {
				tableData = append(tableData, []string{fmt.Sprintf("%d", i+1), t})
			}
			pterm.DefaultTable.WithHasHeader().WithData(pterm.TableData{{"#", "Task Name"}}).WithData(tableData).Render()
			pterm.Println()
		}

		// List features
		features, err := mgr.ListFeatures()
		if err == nil && len(features) > 0 {
			pterm.DefaultSection.Println("Feature Files")
			tableData := pterm.TableData{}
			for i, f := range features {
				tableData = append(tableData, []string{fmt.Sprintf("%d", i+1), f})
			}
			pterm.DefaultTable.WithHasHeader().WithData(pterm.TableData{{"#", "Feature Name"}}).WithData(tableData).Render()
		}

		if len(tasks) == 0 && (err != nil || len(features) == 0) {
			pterm.Info.Println("No tasks or features found.")
			pterm.Println()
			pterm.Println("Run 'spark task init' to initialize task structure.")
		}

		return nil
	},
}

func runDispatchCLI(taskName string) error {
	if taskName == "" {
		return fmt.Errorf("task name is required in CLI mode")
	}

	destPath := viper.GetString("dest")
	mgr := task.NewManager(taskDir, githubOwner, workDir, true)
	return mgr.Dispatch(taskName, destPath)
}

func runDispatchTUI(taskName string) error {
	mgr := task.NewManager(taskDir, githubOwner, workDir, true)

	tasks, err := mgr.ListTasks()
	if err != nil {
		return err
	}

	if len(tasks) == 0 {
		pterm.Warning.Println("No tasks found to dispatch.")
		return nil
	}

	if taskName == "" {
		selected, err := tui.SelectItem("Select a task to dispatch:", tasks)
		if err != nil {
			pterm.Info.Println("Dispatch cancelled.")
			return nil
		}
		taskName = selected
	}

	destPath := viper.GetString("dest")
	confirmed, err := tui.Confirm(fmt.Sprintf("Dispatch task '%s' to GitHub (%s)?", taskName, githubOwner))
	if err != nil || !confirmed {
		pterm.Info.Println("Dispatch cancelled.")
		return nil
	}

	return mgr.Dispatch(taskName, destPath)
}

func runSyncCLI(taskName string) error {
	if taskName == "" {
		return fmt.Errorf("task name is required in CLI mode")
	}

	workPath := viper.GetString("work-path")
	mgr := task.NewManager(taskDir, githubOwner, workDir, true)
	return mgr.SyncBack(taskName, workPath)
}

func runSyncTUI(taskName string) error {
	mgr := task.NewManager(taskDir, githubOwner, workDir, true)

	tasks, err := mgr.ListTasks()
	if err != nil {
		return err
	}

	if len(tasks) == 0 {
		pterm.Warning.Println("No tasks found to sync.")
		return nil
	}

	if taskName == "" {
		selected, err := tui.SelectItem("Select a task to sync back:", tasks)
		if err != nil {
			pterm.Info.Println("Sync cancelled.")
			return nil
		}
		taskName = selected
	}

	workPath := viper.GetString("work-path")
	confirmed, err := tui.Confirm(fmt.Sprintf("Sync task '%s' back to task directory?", taskName))
	if err != nil || !confirmed {
		pterm.Info.Println("Sync cancelled.")
		return nil
	}

	return mgr.SyncBack(taskName, workPath)
}

// Task Feature Commands

var taskInitCmd = &cobra.Command{
	Use:   "init",
	Short: "Initialize task directory structure",
	Long: `Create the default task directory structure with example feature file.

Creates the following directories:
  - tasks/features/
  - tasks/config/
  - tasks/analysis/
  - tasks/mindstorm/
  - tasks/planning/
  - tasks/prd/
  - tasks/example-feature.md

If directories already exist, they will be preserved.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if taskDir == "" {
			taskDir = "."
		}

		mgr := task.NewManager(taskDir, githubOwner, workDir, useTUI)
		return mgr.InitTaskStructure()
	},
}

var taskCreateCmd = &cobra.Command{
	Use:   "create <feature-name>",
	Short: "Create a new feature file",
	Long: `Create a new feature file in tasks/features/ directory.

The feature name will have .md extension added automatically if not provided.
Uses example-feature.md as template.

Example:
  spark task create my-new-feature
  spark task create my-new-feature --content "Custom description"`,
	Args: cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		if taskDir == "" {
			taskDir = "."
		}

		featureName := args[0]
		content, _ := cmd.Flags().GetString("content")

		mgr := task.NewManager(taskDir, githubOwner, workDir, useTUI)
		return mgr.CreateFeature(featureName, content)
	},
}

var taskDeleteCmd = &cobra.Command{
	Use:   "delete <feature-name>",
	Short: "Delete a feature file",
	Long: `Delete a feature file from tasks/features/ directory.

Example:
  spark task delete my-feature
  spark task delete my-feature --force`,
	Args: cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		if taskDir == "" {
			taskDir = "."
		}

		featureName := args[0]
		force, _ := cmd.Flags().GetBool("force")

		mgr := task.NewManager(taskDir, githubOwner, workDir, useTUI)

		if !force && useTUI {
			confirmed, err := tui.Confirm(fmt.Sprintf("Delete feature '%s'?", featureName))
			if err != nil || !confirmed {
				pterm.Info.Println("Delete cancelled.")
				return nil
			}
		}

		return mgr.DeleteFeature(featureName, force)
	},
}

var taskImplCmd = &cobra.Command{
	Use:   "impl <feature-name>",
	Short: "Implement a feature",
	Long: `Execute a feature implementation using kimi CLI and github-task-workflow.

This command will:
  1. Read the feature file
  2. Create a GitHub issue
  3. Execute the task using kimi CLI
  4. Update the issue and commit changes

Requirements:
  - kim CLI must be installed
  - github-task-workflow must be configured

Example:
  spark task impl my-feature
  spark task impl my-feature --tui`,
	Args: cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		if taskDir == "" {
			taskDir = "."
		}

		featureName := args[0]
		mgr := task.NewManager(taskDir, githubOwner, workDir, useTUI)

		return mgr.RunFeature(featureName, useTUI)
	},
}

func init() {
	taskCmd.PersistentFlags().StringVar(&taskDir, "task-dir", "", "Task directory containing all tasks")
	taskCmd.PersistentFlags().StringVar(&githubOwner, "owner", "", "GitHub owner for creating repositories")
	taskCmd.PersistentFlags().StringVar(&workDir, "work-dir", ".", "Working directory for dispatched tasks")
	taskCmd.PersistentFlags().BoolVar(&useTUI, "tui", false, "Enable interactive TUI mode")

	viper.BindPFlag("task_dir", taskCmd.PersistentFlags().Lookup("task-dir"))
	viper.BindPFlag("github_owner", taskCmd.PersistentFlags().Lookup("owner"))
	viper.BindPFlag("work_dir", taskCmd.PersistentFlags().Lookup("work-dir"))

	taskDispatchCmd.Flags().String("dest", "", "Destination path for the dispatched task (default: <work-dir>/<task-name>)")
	taskSyncCmd.Flags().String("work-path", "", "Working path of the task to sync (default: <work-dir>/<task-name>)")

	// Feature command flags
	taskCreateCmd.Flags().String("content", "", "Custom content for the feature file")
	taskDeleteCmd.Flags().Bool("force", false, "Force deletion without confirmation")

	taskCmd.AddCommand(taskDispatchCmd)
	taskCmd.AddCommand(taskSyncCmd)
	taskCmd.AddCommand(taskListCmd)
	taskCmd.AddCommand(taskInitCmd)
	taskCmd.AddCommand(taskCreateCmd)
	taskCmd.AddCommand(taskDeleteCmd)
	taskCmd.AddCommand(taskImplCmd)

	rootCmd.AddCommand(taskCmd)
}
