package resource

import (
	"fmt"
	"os"
	"sort"
	"strings"
	"syscall"
	"time"

	res "spark/internal/resource"

	"github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/spf13/cobra"
)

var (
	onceMode   bool
	exportMode bool
)

var topCmd = &cobra.Command{
	Use:   "top",
	Short: "Display system resource usage (processes, ports, groups)",
	Long: `Monitor system resources with real-time updates.

Examples:
  spark resource top           open interactive TUI
  spark resource top --once     print one resource snapshot
  spark resource top --export   export JSON and Markdown snapshots`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if onceMode {
			printOnce()
		} else if exportMode {
			printExport()
		} else {
			p := tea.NewProgram(
				ResourceModel{
					snapshot: res.CollectSnapshot(false),
					mode:     0,
					sortKey:  0,
					desc:     true,
					width:    120,
					height:   40,
					cursor:   0,
				},
			)
			if _, err := p.Run(); err != nil {
				fmt.Fprintf(os.Stderr, "Error running resource monitor: %v\n", err)
				os.Exit(1)
			}
		}
		return nil
	},
}

func init() {
	topCmd.Flags().BoolVar(&onceMode, "once", false, "Print one resource snapshot and exit")
	topCmd.Flags().BoolVar(&exportMode, "export", false, "Export JSON and Markdown snapshots")
	ResourceCmd.AddCommand(topCmd)
}

var (
	aquaStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("86")).Bold(true)
	whiteStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("255"))
	yellowStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("226"))
	redStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("196"))
	greenStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("82"))
	grayStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("240"))
	orangeStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("208"))
	boldAqua    = lipgloss.NewStyle().Foreground(lipgloss.Color("86")).Bold(true)
	pageSize    = 20
)

type ResourceModel struct {
	snapshot res.Snapshot
	mode     int
	sortKey  int
	desc     bool
	filter   string
	lastKill string
	width    int
	height   int
	cursor   int
	quitted  bool
	ticking  bool
}

func (m ResourceModel) Init() tea.Cmd {
	return nil
}

func (m ResourceModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	if m.quitted {
		return m, tea.Quit
	}

	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height

	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c", "q":
			m.quitted = true
			return m, tea.Quit

		case "tab":
			m.mode = (m.mode + 1) % 3
			if m.mode == 0 {
				if m.sortKey == 4 || m.sortKey == 2 {
					m.sortKey = 0
					m.desc = true
				}
			} else if m.mode == 1 {
				if m.sortKey == 0 || m.sortKey == 1 {
					m.sortKey = 4
					m.desc = false
				}
			} else {
				if m.sortKey == 4 || m.sortKey == 2 {
					m.sortKey = 0
					m.desc = true
				}
			}
			m.cursor = 0

		case "c":
			m.sortKey = 0
			m.desc = true
			m.cursor = 0
		case "m":
			m.sortKey = 1
			m.desc = true
			m.cursor = 0
		case "p":
			m.sortKey = 4
			m.desc = false
			m.cursor = 0
		case "n":
			m.sortKey = 3
			m.desc = false
			m.cursor = 0
		case "i":
			m.sortKey = 2
			m.desc = false
			m.cursor = 0
		case "r":
			m.snapshot = res.CollectSnapshot(false)
			m.cursor = 0
		case "e":
			fresh := res.CollectSnapshot(true)
			m.snapshot = fresh
			result, err := res.ExportSnapshot(fresh, "")
			if err == nil {
				m.lastKill = fmt.Sprintf("exported: %s and %s", result.JSONPath, result.MarkdownPath)
			}

		case "up", "k":
			if m.cursor > 0 {
				m.cursor--
			}
		case "down", "j":
			total := getTotalRows(m.mode, m.snapshot)
			if m.cursor < total-1 {
				m.cursor++
			}
		case "home":
			m.cursor = 0
		case "end":
			total := getTotalRows(m.mode, m.snapshot)
			m.cursor = total - 1
		case "pgup":
			m.cursor -= 10
			if m.cursor < 0 {
				m.cursor = 0
			}
		case "pgdown":
			total := getTotalRows(m.mode, m.snapshot)
			m.cursor += 10
			if m.cursor >= total {
				m.cursor = total - 1
			}

		case "g":
			pid := getCurrentPID(m)
			if pid > 0 {
				m.lastKill = fmt.Sprintf("sent SIGTERM to PID %d", pid)
				syscall.Kill(pid, syscall.SIGTERM)
			}
		case "K":
			pid := getCurrentPID(m)
			if pid > 0 {
				m.lastKill = fmt.Sprintf("sent SIGKILL to PID %d", pid)
				syscall.Kill(pid, syscall.SIGKILL)
			}
		}

	case tickMsg:
		m.snapshot = res.CollectSnapshot(false)
		if !m.ticking {
			m.ticking = true
			return m, tickCmd()
		}
		return m, tickCmd()
	}

	if !m.ticking {
		m.ticking = true
		return m, tickCmd()
	}
	return m, nil
}

type tickMsg time.Time

func tickCmd() tea.Cmd {
	return tea.Tick(time.Second*2, func(t time.Time) tea.Msg {
		return tickMsg(t)
	})
}

func getTotalRows(mode int, snap res.Snapshot) int {
	switch mode {
	case 0:
		return len(snap.Processes)
	case 1:
		return len(snap.Ports)
	case 2:
		return len(snap.Groups)
	}
	return 0
}

func getCurrentPID(m ResourceModel) int {
	switch m.mode {
	case 0:
		procs := filterAndSortProcesses(m.snapshot.Processes, m.sortKey, m.desc)
		total := len(procs)
		if m.cursor >= 0 && m.cursor < total {
			return procs[m.cursor].PID
		}
	case 1:
		ports := filterAndSortPorts(m.snapshot.Ports, m.sortKey, m.desc)
		total := len(ports)
		if m.cursor >= 0 && m.cursor < total {
			return ports[m.cursor].PID
		}
	}
	return 0
}

func (m ResourceModel) View() string {
	w := m.width
	if w < 80 {
		w = 80
	}
	h := m.height
	if h < 20 {
		h = 20
	}

	var b strings.Builder

	b.WriteString(aquaStyle.Render(" Spark Resource Monitor "))
	b.WriteString("\n\n")

	b.WriteString(fmt.Sprintf("  %s %s  %s %s  %s %s\n\n",
		boldAqua.Render("Collected:"), whiteStyle.Render(m.snapshot.CollectedAt.Format("15:04:05")),
		boldAqua.Render("Mode:"), whiteStyle.Render(modeName(m.mode)),
		boldAqua.Render("Sort:"), whiteStyle.Render(sortName(m.sortKey, m.desc))))

	b.WriteString(fmt.Sprintf("  %s %s  %s %s\n",
		boldAqua.Render("Load:"), whiteStyle.Render(m.snapshot.Summary.LoadAvg),
		boldAqua.Render("CPU:"), whiteStyle.Render(m.snapshot.Summary.CPUUsage)))
	b.WriteString(fmt.Sprintf("  %s %s\n",
		boldAqua.Render("Memory:"), whiteStyle.Render(m.snapshot.Summary.Memory)))
	b.WriteString(fmt.Sprintf("  %s %s\n",
		boldAqua.Render("Disk:"), whiteStyle.Render(m.snapshot.Summary.Disk)))
	b.WriteString(fmt.Sprintf("  %s %s\n\n",
		boldAqua.Render("Groups:"), whiteStyle.Render(m.snapshot.Summary.TopGroups)))

	if len(m.snapshot.Errs) > 0 {
		b.WriteString("  " + redStyle.Render("Errors: " + strings.Join(m.snapshot.Errs, " | ")))
		b.WriteString("\n\n")
	} else if m.lastKill != "" {
		b.WriteString("  " + greenStyle.Render(m.lastKill))
		b.WriteString("\n\n")
	}

	headerLines := 11
	tableH := h - headerLines - 3
	if tableH < 5 {
		tableH = 5
	}

	switch m.mode {
	case 0:
		b.WriteString(renderProcessTable(m.snapshot.Processes, m.sortKey, m.desc, m.cursor, tableH, w))
	case 1:
		b.WriteString(renderPortTable(m.snapshot.Ports, m.sortKey, m.desc, m.cursor, tableH, w))
	case 2:
		b.WriteString(renderGroupTable(m.snapshot.Groups, m.sortKey, m.desc, m.cursor, tableH, w))
	}

	b.WriteString("\n")
	total := getTotalRows(m.mode, m.snapshot)
	start := m.cursor + 1
	end := m.cursor + tableH
	if end > total {
		end = total
	}

	b.WriteString(fmt.Sprintf("  %s %s  %s %s  %s %s  %s %s  %s %s  %s %s  %s %s",
		yellowStyle.Render("Tab"), whiteStyle.Render("/g"),
		boldAqua.Render(" view  "),
		yellowStyle.Render("c/m/p/n/i"), whiteStyle.Render(" sort  "),
		yellowStyle.Render("up/down"), whiteStyle.Render(" scroll  "),
		yellowStyle.Render("e"), whiteStyle.Render(" export  "),
		yellowStyle.Render("r"), whiteStyle.Render(" refresh  "),
		yellowStyle.Render("q"), whiteStyle.Render(" quit")))
	b.WriteString(fmt.Sprintf("   [%d-%d/%d]", start, end, total))

	return b.String()
}

func renderProcessTable(procs []res.ProcessInfo, key int, desc bool, cursor int, maxRows int, width int) string {
	procs = filterAndSortProcesses(procs, key, desc)

	total := len(procs)
	if cursor >= total {
		cursor = 0
	}

	pidW := 7
	ppidW := 6
	cpuW := 7
	rssW := 8
	memW := 6
	portW := 8
	groupW := 15
	cmdW := width - pidW - ppidW - cpuW - rssW - memW - portW - groupW - 20

	var b strings.Builder

	b.WriteString("  PID     PPID   CPU%    RSSMiB  MEM%   Ports    Group          Command\n")
	b.WriteString("  " + strings.Repeat("─", width-4) + "\n")

	end := cursor + maxRows
	if end > total {
		end = total
	}

	for i := cursor; i < end; i++ {
		p := procs[i]
		color := whiteStyle
		if p.CPU >= 80 {
			color = redStyle
		} else if p.CPU >= 30 {
			color = orangeStyle
		}

		group := truncate(p.Group, groupW)
		cmd := truncate(p.Command, cmdW)
		ports := truncate(res.PortList(p.Ports), portW)

		prefix := "  "
		if i == cursor {
			prefix = "> "
		}

		line := fmt.Sprintf("%s%-7d %-6d %-7s %-8s %-6s %-8s %-15s %s",
			prefix,
			p.PID, p.PPID,
			color.Render(fmt.Sprintf("%.1f%%", p.CPU)),
			whiteStyle.Render(fmt.Sprintf("%.1f", float64(p.RSSKiB)/1024)),
			whiteStyle.Render(fmt.Sprintf("%.1f", p.Mem)),
			grayStyle.Render(ports),
			whiteStyle.Render(group),
			whiteStyle.Render(cmd))

		b.WriteString(line)
		b.WriteString("\n")
	}

	return b.String()
}

func renderPortTable(ports []res.PortInfo, key int, desc bool, cursor int, maxRows int, width int) string {
	ports = filterAndSortPorts(ports, key, desc)

	total := len(ports)
	if cursor >= total {
		cursor = 0
	}

	portW := 7
	protoW := 6
	pidW := 7
	addrW := (width - portW - protoW - pidW - 20) / 2
	cmdW := width - portW - protoW - pidW - addrW - 15

	var b strings.Builder

	b.WriteString(fmt.Sprintf("  %-7s %-6s %-7s %-%ds %s\n", "Port", "Proto", "PID", addrW, "Command"))
	b.WriteString("  " + strings.Repeat("─", width-4) + "\n")

	end := cursor + maxRows
	if end > total {
		end = total
	}

	for i := cursor; i < end; i++ {
		p := ports[i]
		addr := truncate(p.Address, addrW)
		cmd := truncate(p.Command, cmdW)

		prefix := "  "
		if i == cursor {
			prefix = "> "
		}

		line := fmt.Sprintf("%s%-7d %-6s %-7d %-%ds %s",
			prefix,
			p.Port, p.Protocol, p.PID,
			whiteStyle.Render(addr),
			whiteStyle.Render(cmd))

		b.WriteString(line)
		b.WriteString("\n")
	}

	return b.String()
}

func renderGroupTable(groups []res.GroupInfo, key int, desc bool, cursor int, maxRows int, width int) string {
	groups = filterAndSortGroups(groups, key, desc)

	total := len(groups)
	if cursor >= total {
		cursor = 0
	}

	cpuW := 7
	rssW := 8
	countW := 6
	portW := 10
	groupW := (width - cpuW - rssW - countW - portW - 20) / 2
	cmdW := width - cpuW - rssW - countW - portW - groupW - 15

	var b strings.Builder

	b.WriteString(fmt.Sprintf("  %-7s %-8s %-6s %-10s %-%ds %s\n", "CPU%", "RSSMiB", "Procs", "Ports", groupW, "Group"))
	b.WriteString("  " + strings.Repeat("─", width-4) + "\n")

	end := cursor + maxRows
	if end > total {
		end = total
	}

	for i := cursor; i < end; i++ {
		g := groups[i]
		color := whiteStyle
		if g.CPU >= 80 {
			color = redStyle
		} else if g.CPU >= 30 {
			color = orangeStyle
		}

		group := truncate(g.Name, groupW)
		pids := truncate(res.IntList(g.TopPIDs, 4), cmdW)
		ports := truncate(res.IntList(g.Ports, 6), portW)

		prefix := "  "
		if i == cursor {
			prefix = "> "
		}

		line := fmt.Sprintf("%s%-7s %-8s %-6d %-10s %-%ds %s",
			prefix,
			color.Render(fmt.Sprintf("%.1f%%", g.CPU)),
			whiteStyle.Render(fmt.Sprintf("%.1f", float64(g.RSSKiB)/1024)),
			g.Count,
			grayStyle.Render(ports),
			whiteStyle.Render(group),
			grayStyle.Render(pids))

		b.WriteString(line)
		b.WriteString("\n")
	}

	return b.String()
}

func filterAndSortProcesses(procs []res.ProcessInfo, key int, desc bool) []res.ProcessInfo {
	sort.SliceStable(procs, func(i, j int) bool {
		cmp := 0
		switch key {
		case 1:
			cmp = res.CompareInt(procs[i].RSSKiB, procs[j].RSSKiB)
		case 2:
			cmp = res.CompareInt(procs[i].PID, procs[j].PID)
		case 3:
			cmp = strings.Compare(strings.ToLower(procs[i].Command), strings.ToLower(procs[j].Command))
		case 4:
			cmp = res.CompareInt(res.FirstPort(procs[i].Ports), res.FirstPort(procs[j].Ports))
		default:
			cmp = res.CompareFloat(procs[i].CPU, procs[j].CPU)
		}
		if cmp == 0 {
			cmp = res.CompareInt(procs[i].PID, procs[j].PID)
		}
		if desc {
			return cmp > 0
		}
		return cmp < 0
	})
	return procs
}

func filterAndSortPorts(ports []res.PortInfo, key int, desc bool) []res.PortInfo {
	sort.SliceStable(ports, func(i, j int) bool {
		cmp := 0
		switch key {
		case 2:
			cmp = res.CompareInt(ports[i].PID, ports[j].PID)
		case 3:
			cmp = strings.Compare(strings.ToLower(ports[i].Command), strings.ToLower(ports[j].Command))
		default:
			cmp = res.CompareInt(ports[i].Port, ports[j].Port)
		}
		if cmp == 0 {
			cmp = res.CompareInt(ports[i].PID, ports[j].PID)
		}
		if desc {
			return cmp > 0
		}
		return cmp < 0
	})
	return ports
}

func filterAndSortGroups(groups []res.GroupInfo, key int, desc bool) []res.GroupInfo {
	sort.SliceStable(groups, func(i, j int) bool {
		cmp := 0
		switch key {
		case 1:
			cmp = res.CompareInt(groups[i].RSSKiB, groups[j].RSSKiB)
		case 3:
			cmp = strings.Compare(strings.ToLower(groups[i].Name), strings.ToLower(groups[j].Name))
		default:
			cmp = res.CompareFloat(groups[i].CPU, groups[j].CPU)
		}
		if cmp == 0 {
			cmp = strings.Compare(groups[i].Name, groups[j].Name)
		}
		if desc {
			return cmp > 0
		}
		return cmp < 0
	})
	return groups
}

func truncate(s string, max int) string {
	if max < 4 {
		max = 4
	}
	w := lipgloss.Width(s)
	if w > max {
		return s[:max-3] + "..."
	}
	return s
}

func modeName(mode int) string {
	switch mode {
	case 0:
		return "processes"
	case 1:
		return "ports"
	case 2:
		return "groups"
	}
	return "unknown"
}

func sortName(key int, desc bool) string {
	name := ""
	switch key {
	case 0:
		name = "CPU"
	case 1:
		name = "Memory"
	case 2:
		name = "PID"
	case 3:
		name = "Name"
	case 4:
		name = "Port"
	}
	if desc {
		return name + " desc"
	}
	return name + " asc"
}

func printOnce() {
	snap := res.CollectSnapshot(true)
	fmt.Printf("Collected: %s\n", snap.CollectedAt.Format("2006-01-02 15:04:05"))
	fmt.Printf("Load: %s\n", snap.Summary.LoadAvg)
	fmt.Printf("CPU: %s\n", snap.Summary.CPUUsage)
	fmt.Printf("Memory: %s\n", snap.Summary.Memory)
	fmt.Printf("Disk: %s\n", snap.Summary.Disk)
	fmt.Printf("Groups: %s\n", snap.Summary.TopGroups)
	if len(snap.Errs) > 0 {
		fmt.Printf("Errors: %s\n", snap.Errs)
	}

	processes := make([]res.ProcessInfo, len(snap.Processes))
	copy(processes, snap.Processes)
	sort.SliceStable(processes, func(i, j int) bool { return processes[i].CPU > processes[j].CPU })
	fmt.Println("\nTop CPU:")
	for i, proc := range processes {
		if i >= 30 {
			break
		}
		fmt.Printf("  %6d  %6.1f%% CPU  %8.1f MiB  %-22s %s\n", proc.PID, proc.CPU, float64(proc.RSSKiB)/1024, proc.Group, res.ShortenForPrint(proc.Command, 90))
	}

	groups := make([]res.GroupInfo, len(snap.Groups))
	copy(groups, snap.Groups)
	sort.SliceStable(groups, func(i, j int) bool { return groups[i].CPU > groups[j].CPU })
	fmt.Println("\nGroups by CPU:")
	for i, group := range groups {
		if i >= 20 {
			break
		}
		fmt.Printf("  %7.1f%% CPU  %8.1f MiB  %4d procs  %-24s ports=%s\n", group.CPU, float64(group.RSSKiB)/1024, group.Count, group.Name, res.IntList(group.Ports, 8))
	}

	ports := make([]res.PortInfo, len(snap.Ports))
	copy(ports, snap.Ports)
	sort.SliceStable(ports, func(i, j int) bool { return ports[i].Port < ports[j].Port })
	fmt.Println("\nPorts / sockets:")
	for i, port := range ports {
		if i >= 50 {
			break
		}
		fmt.Printf("  %6d/%-3s  PID %-6d  %-28s %s\n", port.Port, port.Protocol, port.PID, port.Command, port.Address)
	}

	if len(snap.ChromeTabs) > 0 {
		fmt.Println("\nChrome tabs:")
		for i, tab := range snap.ChromeTabs {
			if i >= 20 {
				break
			}
			fmt.Printf("  W%d T%d  %s  %s\n", tab.Window, tab.Index, res.ShortenForPrint(tab.Title, 54), res.ShortenForPrint(tab.URL, 96))
		}
	}
}

func printExport() {
	snap := res.CollectSnapshot(true)
	result, err := res.ExportSnapshot(snap, "")
	if err != nil {
		fmt.Fprintf(os.Stderr, "export failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Exported JSON: %s\n", result.JSONPath)
	fmt.Printf("Exported Markdown: %s\n", result.MarkdownPath)
}