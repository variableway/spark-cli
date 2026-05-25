package resource

import (
	"testing"

	res "spark/internal/resource"

	"github.com/charmbracelet/bubbletea"
)

func TestKillKeyWithKeyRunes(t *testing.T) {
	m := ResourceModel{
		snapshot: res.Snapshot{
			Processes: []res.ProcessInfo{
				{PID: 1234, Command: "test-process", CPU: 1.0, RSSKiB: 100},
			},
		},
		mode:   0,
		cursor: 0,
	}

	msg := tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'K'}}
	result, _ := m.Update(msg)
	model := result.(ResourceModel)

	if model.lastKill == "" {
		t.Error("expected lastKill to be set when pressing 'K' via KeyRunes")
	}
}

func TestKillKeyWithKeyType(t *testing.T) {
	m := ResourceModel{
		snapshot: res.Snapshot{
			Processes: []res.ProcessInfo{
				{PID: 1234, Command: "test-process", CPU: 1.0, RSSKiB: 100},
			},
		},
		mode:   0,
		cursor: 0,
	}

	msg := tea.KeyMsg{Type: tea.KeyType('K')}
	result, _ := m.Update(msg)
	model := result.(ResourceModel)

	if model.lastKill == "" {
		t.Error("expected lastKill to be set when pressing 'K' via KeyType")
	}
}

func TestKillKeyNoProcessSelected(t *testing.T) {
	m := ResourceModel{
		snapshot: res.Snapshot{
			Processes: []res.ProcessInfo{},
		},
		mode:   0,
		cursor: 0,
	}

	msg := tea.KeyMsg{Type: tea.KeyType('K')}
	result, _ := m.Update(msg)
	model := result.(ResourceModel)

	if model.lastKill != "no process selected" {
		t.Errorf("expected 'no process selected', got '%s'", model.lastKill)
	}
}

func TestKillKeyLowercaseKMovesCursor(t *testing.T) {
	m := ResourceModel{
		snapshot: res.Snapshot{
			Processes: []res.ProcessInfo{
				{PID: 1, Command: "p1", CPU: 1.0, RSSKiB: 100},
				{PID: 2, Command: "p2", CPU: 2.0, RSSKiB: 200},
			},
		},
		mode:   0,
		cursor: 1,
	}

	msg := tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'k'}}
	result, _ := m.Update(msg)
	model := result.(ResourceModel)

	if model.cursor != 0 {
		t.Errorf("expected cursor to move to 0, got %d", model.cursor)
	}
	if model.lastKill != "" {
		t.Errorf("expected lastKill to be empty for lowercase 'k', got '%s'", model.lastKill)
	}
}

func TestKillKeyInPortsMode(t *testing.T) {
	m := ResourceModel{
		snapshot: res.Snapshot{
			Ports: []res.PortInfo{
				{Port: 8080, Protocol: "TCP", PID: 5678, Address: "127.0.0.1", Command: "node"},
			},
		},
		mode:   1,
		cursor: 0,
	}

	msg := tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'K'}}
	result, _ := m.Update(msg)
	model := result.(ResourceModel)

	if model.lastKill == "" {
		t.Error("expected lastKill to be set when pressing 'K' in ports mode")
	}
}

func TestGracefulKillKeyG(t *testing.T) {
	m := ResourceModel{
		snapshot: res.Snapshot{
			Processes: []res.ProcessInfo{
				{PID: 1234, Command: "test-process", CPU: 1.0, RSSKiB: 100},
			},
		},
		mode:   0,
		cursor: 0,
	}

	msg := tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'g'}}
	result, _ := m.Update(msg)
	model := result.(ResourceModel)

	if model.lastKill == "" {
		t.Error("expected lastKill to be set when pressing 'g'")
	}
}

func TestArrowUpViaKeyType(t *testing.T) {
	procs := make([]res.ProcessInfo, 5)
	for i := range procs {
		procs[i] = res.ProcessInfo{PID: i + 1, Command: "p", CPU: 1.0, RSSKiB: 100}
	}
	m := ResourceModel{
		snapshot: res.Snapshot{Processes: procs},
		mode:     0,
		cursor:   3,
	}

	msg := tea.KeyMsg{Type: tea.KeyUp}
	result, _ := m.Update(msg)
	model := result.(ResourceModel)

	if model.cursor != 2 {
		t.Errorf("expected cursor 2 after KeyUp from 3, got %d", model.cursor)
	}
}

func TestArrowDownViaKeyType(t *testing.T) {
	procs := make([]res.ProcessInfo, 5)
	for i := range procs {
		procs[i] = res.ProcessInfo{PID: i + 1, Command: "p", CPU: 1.0, RSSKiB: 100}
	}
	m := ResourceModel{
		snapshot: res.Snapshot{Processes: procs},
		mode:     0,
		cursor:   1,
	}

	msg := tea.KeyMsg{Type: tea.KeyDown}
	result, _ := m.Update(msg)
	model := result.(ResourceModel)

	if model.cursor != 2 {
		t.Errorf("expected cursor 2 after KeyDown from 1, got %d", model.cursor)
	}
}

func TestHomeKeyViaKeyType(t *testing.T) {
	procs := make([]res.ProcessInfo, 5)
	for i := range procs {
		procs[i] = res.ProcessInfo{PID: i + 1, Command: "p", CPU: 1.0, RSSKiB: 100}
	}
	m := ResourceModel{
		snapshot: res.Snapshot{Processes: procs},
		mode:     0,
		cursor:   3,
	}

	msg := tea.KeyMsg{Type: tea.KeyHome}
	result, _ := m.Update(msg)
	model := result.(ResourceModel)

	if model.cursor != 0 {
		t.Errorf("expected cursor 0 after Home, got %d", model.cursor)
	}
}

func TestEndKeyViaKeyType(t *testing.T) {
	procs := make([]res.ProcessInfo, 5)
	for i := range procs {
		procs[i] = res.ProcessInfo{PID: i + 1, Command: "p", CPU: 1.0, RSSKiB: 100}
	}
	m := ResourceModel{
		snapshot: res.Snapshot{Processes: procs},
		mode:     0,
		cursor:   0,
	}

	msg := tea.KeyMsg{Type: tea.KeyEnd}
	result, _ := m.Update(msg)
	model := result.(ResourceModel)

	if model.cursor != 4 {
		t.Errorf("expected cursor 4 after End, got %d", model.cursor)
	}
}
