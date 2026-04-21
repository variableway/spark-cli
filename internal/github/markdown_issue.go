package github

import (
	"fmt"
	"os"
	"regexp"
	"strings"
)

// Task represents a task parsed from markdown
type Task struct {
	ID      string
	Title   string
	Content string
}

// TaskParser parses tasks from markdown content
type TaskParser struct {
	taskPattern *regexp.Regexp
}

// NewTaskParser creates a new task parser
func NewTaskParser() *TaskParser {
	return &TaskParser{
		taskPattern: regexp.MustCompile(`(?m)^#{1,2}\s+Task\s+(\d+)[\s:]*(.+)?$`),
	}
}

// ParseTasks parses tasks from markdown content
func (p *TaskParser) ParseTasks(content string) []Task {
	var tasks []Task
	matches := p.taskPattern.FindAllStringSubmatchIndex(content, -1)

	for i, match := range matches {
		start := match[0]
		end := len(content)
		if i < len(matches)-1 {
			end = matches[i+1][0]
		}

		taskContent := content[start:end]
		task := p.parseTask(taskContent)
		if task.ID != "" {
			tasks = append(tasks, task)
		}
	}

	return tasks
}

// parseTask parses a single task from content
func (p *TaskParser) parseTask(content string) Task {
	lines := strings.Split(content, "\n")
	if len(lines) == 0 {
		return Task{}
	}

	// Parse header line
	headerMatch := p.taskPattern.FindStringSubmatch(lines[0])
	if headerMatch == nil {
		return Task{}
	}

	taskID := headerMatch[1]
	title := strings.TrimSpace(headerMatch[2])
	if title == "" {
		title = fmt.Sprintf("Task %s", taskID)
	}

	// Parse content (remaining lines)
	var contentLines []string
	for i := 1; i < len(lines); i++ {
		line := lines[i]
		// Stop at next task or major heading
		if strings.HasPrefix(line, "## ") && !strings.HasPrefix(line, "## Task") {
			break
		}
		contentLines = append(contentLines, line)
	}

	// Clean up content
	body := strings.TrimSpace(strings.Join(contentLines, "\n"))

	return Task{
		ID:      taskID,
		Title:   title,
		Content: body,
	}
}

// MarkdownIssueCreator creates GitHub issues from markdown files
type MarkdownIssueCreator struct {
	parser *TaskParser
	repo   string
}

// NewMarkdownIssueCreator creates a new markdown issue creator
func NewMarkdownIssueCreator(repo string) *MarkdownIssueCreator {
	return &MarkdownIssueCreator{
		parser: NewTaskParser(),
		repo:   repo,
	}
}

// CreateIssuesFromFile creates GitHub issues from a markdown file
func (c *MarkdownIssueCreator) CreateIssuesFromFile(filePath string, labels []string) error {
	content, err := os.ReadFile(filePath)
	if err != nil {
		return fmt.Errorf("failed to read file '%s': %w", filePath, err)
	}

	tasks := c.parser.ParseTasks(string(content))
	if len(tasks) == 0 {
		return fmt.Errorf("no tasks found in '%s' (expected format: '## Task <id>: title')", filePath)
	}

	fmt.Printf("Found %d task(s) in %s\n", len(tasks), filePath)

	for _, task := range tasks {
		body := c.formatIssueBody(task)
		if err := CreateIssue(c.repo, task.Title, body, labels); err != nil {
			return fmt.Errorf("failed to create issue for task %s: %w", task.ID, err)
		}
		fmt.Printf("✓ Created issue: %s\n", task.Title)
	}

	return nil
}

// formatIssueBody formats the issue body from task content
func (c *MarkdownIssueCreator) formatIssueBody(task Task) string {
	var parts []string

	if task.Content != "" {
		parts = append(parts, task.Content)
	}

	parts = append(parts, fmt.Sprintf("\n---\n*Task ID: %s*", task.ID))

	return strings.Join(parts, "\n")
}

// PreviewTasks previews tasks from a markdown file without creating issues
func (c *MarkdownIssueCreator) PreviewTasks(filePath string) ([]Task, error) {
	content, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to read file '%s': %w", filePath, err)
	}

	tasks := c.parser.ParseTasks(string(content))
	return tasks, nil
}
