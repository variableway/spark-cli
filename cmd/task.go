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
  monolize task dispatch my-task --dest ./workspace/my-task
  monolize task dispatch --tui`,
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
  monolize task sync my-task --work-path ./workspace/my-task
  monolize task sync --tui`,
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
	Short: "List all tasks in the task directory",
	Long:  `List all tasks (directories) in the configured task directory.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if taskDir == "" {
			return fmt.Errorf("task directory is required, use --task-dir or set in config")
		}

		mgr := task.NewManager(taskDir, githubOwner, workDir, false)
		tasks, err := mgr.ListTasks()
		if err != nil {
			return err
		}

		if len(tasks) == 0 {
			pterm.Info.Println("No tasks found.")
			return nil
		}

		if useTUI {
			pterm.DefaultHeader.WithFullWidth().Println("Task List")
			pterm.Println()
			var listItems []pterm.BulletListItem
			for _, t := range tasks {
				listItems = append(listItems, pterm.BulletListItem{Level: 0, Text: t})
			}
			pterm.DefaultBulletList.WithItems(listItems).Render()
		} else {
			pterm.DefaultSection.Printf("Tasks in %s", taskDir)
			tableData := pterm.TableData{}
			for i, t := range tasks {
				tableData = append(tableData, []string{fmt.Sprintf("%d", i+1), t})
			}
			pterm.DefaultTable.WithHasHeader().WithData(pterm.TableData{{"#", "Task Name"}}).WithData(tableData).Render()
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

	taskCmd.AddCommand(taskDispatchCmd)
	taskCmd.AddCommand(taskSyncCmd)
	taskCmd.AddCommand(taskListCmd)

	rootCmd.AddCommand(taskCmd)
}
