package github

import (
	"testing"
)

func TestTaskParser_ParseTasks(t *testing.T) {
	parser := NewTaskParser()

	tests := []struct {
		name          string
		content       string
		expectedCount int
		expectedIDs   []string
		expectedTitles []string
	}{
		{
			name: "single task",
			content: `## Task 1: First Task
This is the content of the first task.
With multiple lines.`,
			expectedCount: 1,
			expectedIDs:   []string{"1"},
			expectedTitles: []string{"First Task"},
		},
		{
			name: "multiple tasks",
			content: `## Task 1: First Task
Content of first task.

## Task 2: Second Task
Content of second task.`,
			expectedCount: 2,
			expectedIDs:   []string{"1", "2"},
			expectedTitles: []string{"First Task", "Second Task"},
		},
		{
			name: "task without title",
			content: `## Task 1
Content without explicit title.`,
			expectedCount: 1,
			expectedIDs:   []string{"1"},
			expectedTitles: []string{"Task 1"},
		},
		{
			name: "task with colon in title",
			content: `## Task 1: Title with: colon
Content here.`,
			expectedCount: 1,
			expectedIDs:   []string{"1"},
			expectedTitles: []string{"Title with: colon"},
		},
		{
			name: "stops at non-task headings",
			content: `## Task 1: First Task
Content here.

## Some Other Heading
This should not be included.`,
			expectedCount: 1,
			expectedIDs:   []string{"1"},
			expectedTitles: []string{"First Task"},
		},
		{
			name: "no tasks in content",
			content: `# Regular Markdown
Some content here.

## Another Heading
More content.`,
			expectedCount: 0,
		},
		{
			name:          "empty content",
			content:       "",
			expectedCount: 0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			tasks := parser.ParseTasks(tt.content)

			if len(tasks) != tt.expectedCount {
				t.Errorf("expected %d tasks, got %d", tt.expectedCount, len(tasks))
			}

			for i, task := range tasks {
				if i < len(tt.expectedIDs) && task.ID != tt.expectedIDs[i] {
					t.Errorf("task %d: expected ID %q, got %q", i, tt.expectedIDs[i], task.ID)
				}
				if i < len(tt.expectedTitles) && task.Title != tt.expectedTitles[i] {
					t.Errorf("task %d: expected title %q, got %q", i, tt.expectedTitles[i], task.Title)
				}
			}
		})
	}
}

func TestTaskParser_ParseTasks_ContentExtraction(t *testing.T) {
	parser := NewTaskParser()

	t.Run("extracts task content correctly", func(t *testing.T) {
		content := `## Task 1: Test Task
Line 1
Line 2
Line 3`

		tasks := parser.ParseTasks(content)

		if len(tasks) != 1 {
			t.Fatalf("expected 1 task, got %d", len(tasks))
		}

		expectedContent := "Line 1\nLine 2\nLine 3"
		if tasks[0].Content != expectedContent {
			t.Errorf("expected content %q, got %q", expectedContent, tasks[0].Content)
		}
	})

	t.Run("excludes next task from content", func(t *testing.T) {
		content := `## Task 1: First
Content for first task.

## Task 2: Second
Content for second task.`

		tasks := parser.ParseTasks(content)

		if len(tasks) != 2 {
			t.Fatalf("expected 2 tasks, got %d", len(tasks))
		}

		if tasks[0].Content == "" {
			t.Error("first task should have content")
		}

		if tasks[0].Content == tasks[1].Content {
			t.Error("tasks should have different content")
		}
	})
}

func TestMarkdownIssueCreator_PreviewTasks_FileNotFound(t *testing.T) {
	creator := NewMarkdownIssueCreator("owner/repo")

	_, err := creator.PreviewTasks("/nonexistent/file.md")
	if err == nil {
		t.Error("expected error for non-existent file")
	}
}

func TestMarkdownIssueCreator_formatIssueBody(t *testing.T) {
	creator := NewMarkdownIssueCreator("owner/repo")

	tests := []struct {
		name     string
		task     Task
		expected string
	}{
		{
			name: "task with content",
			task: Task{
				ID:      "1",
				Title:   "Test Task",
				Content: "Task description here.",
			},
			expected: "Task description here.\n\n---\n*Task ID: 1*",
		},
		{
			name: "task without content",
			task: Task{
				ID:      "2",
				Title:   "Empty Task",
				Content: "",
			},
			expected: "\n---\n*Task ID: 2*",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := creator.formatIssueBody(tt.task)
			if result != tt.expected {
				t.Errorf("expected %q, got %q", tt.expected, result)
			}
		})
	}
}
