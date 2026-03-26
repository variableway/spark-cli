package tui

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

var (
	selectedStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("170")).Bold(true)
	itemStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("252"))
	titleStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("205")).Bold(true)
	quitStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("241"))
)

type SelectModel struct {
	items    []string
	cursor   int
	selected string
	title    string
	quitted  bool
}

func NewSelectModel(title string, items []string) SelectModel {
	return SelectModel{
		items: items,
		title: title,
	}
}

func (m SelectModel) Init() tea.Cmd {
	return nil
}

func (m SelectModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c", "q":
			m.quitted = true
			return m, tea.Quit
		case "up", "k":
			if m.cursor > 0 {
				m.cursor--
			}
		case "down", "j":
			if m.cursor < len(m.items)-1 {
				m.cursor++
			}
		case "enter", " ":
			m.selected = m.items[m.cursor]
			return m, tea.Quit
		}
	}
	return m, nil
}

func (m SelectModel) View() string {
	var b strings.Builder
	b.WriteString(titleStyle.Render(m.title))
	b.WriteString("\n\n")

	for i, item := range m.items {
		if m.cursor == i {
			b.WriteString(selectedStyle.Render("→ " + item))
		} else {
			b.WriteString(itemStyle.Render("  " + item))
		}
		b.WriteString("\n")
	}

	b.WriteString("\n")
	b.WriteString(quitStyle.Render("↑/↓: navigate, Enter: select, q: quit"))
	return b.String()
}

func (m SelectModel) GetSelected() string {
	return m.selected
}

func (m SelectModel) WasQuitted() bool {
	return m.quitted
}

func SelectItem(title string, items []string) (string, error) {
	if len(items) == 0 {
		return "", fmt.Errorf("no items to select")
	}
	p := tea.NewProgram(NewSelectModel(title, items))
	m, err := p.Run()
	if err != nil {
		return "", err
	}
	model := m.(SelectModel)
	if model.WasQuitted() {
		return "", fmt.Errorf("selection cancelled")
	}
	return model.GetSelected(), nil
}
