package tui

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

var (
	confirmYesStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("42")).Bold(true)
	confirmNoStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("203")).Bold(true)
	confirmBoxStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("63")).
			Padding(1, 2)
)

type ConfirmModel struct {
	message string
	yes     bool
	cursor  bool
	quitted bool
}

func NewConfirmModel(message string) ConfirmModel {
	return ConfirmModel{
		message: message,
		yes:     true,
		cursor:  true,
	}
}

func (m ConfirmModel) Init() tea.Cmd {
	return nil
}

func (m ConfirmModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c", "q":
			m.quitted = true
			return m, tea.Quit
		case "left", "right", "h", "l", "tab":
			m.yes = !m.yes
		case "enter", " ":
			m.cursor = false
			return m, tea.Quit
		case "y", "Y":
			m.yes = true
			m.cursor = false
			return m, tea.Quit
		case "n", "N":
			m.yes = false
			m.cursor = false
			return m, tea.Quit
		}
	}
	return m, nil
}

func (m ConfirmModel) View() string {
	var b strings.Builder
	b.WriteString(confirmBoxStyle.Render(m.message))
	b.WriteString("\n\n")

	yesText := " Yes "
	noText := " No  "

	if m.yes {
		yesText = confirmYesStyle.Render("[Yes]")
		noText = confirmNoStyle.Render(" No  ")
	} else {
		yesText = confirmYesStyle.Render(" Yes ")
		noText = confirmNoStyle.Render("[No]")
	}

	b.WriteString(yesText)
	b.WriteString("  ")
	b.WriteString(noText)
	b.WriteString("\n\n")
	b.WriteString(quitStyle.Render("←/→: toggle, Enter: confirm, y/n: quick select"))
	return b.String()
}

func (m ConfirmModel) IsConfirmed() bool {
	return m.yes
}

func (m ConfirmModel) WasQuitted() bool {
	return m.quitted
}

func Confirm(message string) (bool, error) {
	p := tea.NewProgram(NewConfirmModel(message))
	m, err := p.Run()
	if err != nil {
		return false, err
	}
	model := m.(ConfirmModel)
	if model.WasQuitted() {
		return false, fmt.Errorf("confirmation cancelled")
	}
	return model.IsConfirmed(), nil
}
