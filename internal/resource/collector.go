package resource

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
)

const RefreshEvery = 2 * time.Second

type ViewMode int

const (
	ViewProcesses ViewMode = iota
	ViewPorts
	ViewGroups
)

type SortKey int

const (
	SortCPU SortKey = iota
	SortMemory
	SortPID
	SortName
	SortPort
)

type ProcessInfo struct {
	PID     int
	PPID    int
	User    string
	CPU     float64
	Mem     float64
	RSSKiB  int
	State   string
	Elapsed string
	Command string
	Group   string
	Ports   []PortInfo
}

type GroupInfo struct {
	Name        string
	CPU         float64
	RSSKiB      int
	Count       int
	Ports       []int
	TopPIDs     []int
	TopCommands []string
}

type PortInfo struct {
	PID      int
	Command  string
	Protocol string
	Address  string
	Port     int
}

type ChromeTabInfo struct {
	Window int
	Index  int
	Title  string
	URL    string
}

type Snapshot struct {
	CollectedAt time.Time
	Processes   []ProcessInfo
	Ports       []PortInfo
	Groups      []GroupInfo
	ChromeTabs  []ChromeTabInfo
	Summary     SummaryInfo
	Errs        []string
}

type SummaryInfo struct {
	LoadAvg    string
	CPUUsage   string
	Memory     string
	Disk       string
	ProcCount  int
	PortCount  int
	TopGroups  string
	LastAction string
}

type ExportResult struct {
	JSONPath     string
	MarkdownPath string
}

var (
	portPattern = regexp.MustCompile(`:(\d+)(?:\s|$)`)
	groupRules  = []struct {
		name string
		re   *regexp.Regexp
	}{
		{"Yorun client/dev stack", regexp.MustCompile(`(?i)yorun-qa|qaworkspace|tauri\.js dev|vite\.js|qa serve|start-client\.sh`)},
		{"Google Chrome", regexp.MustCompile(`(?i)Google Chrome`)},
		{"Trae", regexp.MustCompile(`(?i)Trae\.app`)},
		{"Codex", regexp.MustCompile(`(?i)Codex\.app`)},
		{"WindowServer", regexp.MustCompile(`(?i)WindowServer`)},
		{"duetexpertd", regexp.MustCompile(`(?i)duetexpertd`)},
		{"opendirectoryd", regexp.MustCompile(`(?i)opendirectoryd`)},
	}
)

func CollectSnapshot(includeChromeTabs bool) Snapshot {
	errs := make([]string, 0)
	procs, err := CollectProcesses()
	if err != nil {
		errs = append(errs, err.Error())
	}
	ports, err := CollectPorts()
	if err != nil {
		errs = append(errs, err.Error())
	}
	portsByPID := make(map[int][]PortInfo)
	for _, port := range ports {
		portsByPID[port.PID] = append(portsByPID[port.PID], port)
	}
	for i := range procs {
		procs[i].Ports = portsByPID[procs[i].PID]
		procs[i].Group = ProcessGroup(procs[i].Command)
	}
	groups := AggregateGroups(procs)
	var chromeTabs []ChromeTabInfo
	if includeChromeTabs {
		var chromeErr error
		chromeTabs, chromeErr = CollectChromeTabs()
		if chromeErr != nil {
			errs = append(errs, chromeErr.Error())
		}
	}
	summary := CollectSummary(procs, ports, groups)
	return Snapshot{
		CollectedAt: time.Now(),
		Processes:   procs,
		Ports:       ports,
		Groups:      groups,
		ChromeTabs:  chromeTabs,
		Summary:      summary,
		Errs:         errs,
	}
}

func CollectProcesses() ([]ProcessInfo, error) {
	output, err := RunCommand(3*time.Second, "ps", "-axo", "pid=,ppid=,user=,pcpu=,pmem=,rss=,state=,etime=,command=")
	if err != nil {
		return nil, err
	}
	var processes []ProcessInfo
	scanner := bufio.NewScanner(bytes.NewReader(output))
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) < 9 {
			continue
		}
		pid, err1 := strconv.Atoi(fields[0])
		ppid, err2 := strconv.Atoi(fields[1])
		cpu, err3 := strconv.ParseFloat(fields[3], 64)
		mem, err4 := strconv.ParseFloat(fields[4], 64)
		rss, err5 := strconv.Atoi(fields[5])
		if err1 != nil || err2 != nil || err3 != nil || err4 != nil || err5 != nil {
			continue
		}
		processes = append(processes, ProcessInfo{
			PID:     pid,
			PPID:    ppid,
			User:    fields[2],
			CPU:     cpu,
			Mem:     mem,
			RSSKiB:  rss,
			State:   fields[6],
			Elapsed: fields[7],
			Command: strings.Join(fields[8:], " "),
		})
	}
	return processes, scanner.Err()
}

func CollectPorts() ([]PortInfo, error) {
	ports, err := CollectPortsByProtocol("TCP", "lsof", "-nP", "-iTCP", "-sTCP:LISTEN", "-F", "pcn")
	if err != nil {
		return nil, err
	}
	udpPorts, _ := CollectPortsByProtocol("UDP", "lsof", "-nP", "-iUDP", "-F", "pcn")
	ports = append(ports, udpPorts...)
	sort.SliceStable(ports, func(i, j int) bool {
		if ports[i].Port == ports[j].Port {
			return ports[i].PID < ports[j].PID
		}
		return ports[i].Port < ports[j].Port
	})
	return ports, nil
}

func CollectPortsByProtocol(protocol string, args ...string) ([]PortInfo, error) {
	if len(args) == 0 {
		return nil, nil
	}
	output, err := RunCommand(3*time.Second, args[0], args[1:]...)
	if err != nil {
		if len(output) == 0 {
			return nil, err
		}
	}
	var ports []PortInfo
	pid := 0
	command := ""
	scanner := bufio.NewScanner(bytes.NewReader(output))
	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue
		}
		switch line[0] {
		case 'p':
			pid, _ = strconv.Atoi(strings.TrimSpace(line[1:]))
		case 'c':
			command = strings.TrimSpace(line[1:])
		case 'n':
			address := strings.TrimSpace(line[1:])
			port := ParsePort(address)
			if pid > 0 && port > 0 {
				ports = append(ports, PortInfo{PID: pid, Command: command, Protocol: protocol, Address: address, Port: port})
			}
		}
	}
	return ports, scanner.Err()
}

func CollectChromeTabs() ([]ChromeTabInfo, error) {
	if _, err := RunCommand(1*time.Second, "pgrep", "-x", "Google Chrome"); err != nil {
		return nil, nil
	}
	script := `
set output to ""
tell application "Google Chrome"
  repeat with w from 1 to count of windows
    set tabCount to count of tabs of window w
    repeat with t from 1 to tabCount
      set tabTitle to title of tab t of window w
      set tabURL to URL of tab t of window w
      set output to output & w & "|||" & t & "|||" & tabTitle & "|||" & tabURL & linefeed
    end repeat
  end repeat
end tell
return output
`
	output, err := RunCommand(8*time.Second, "osascript", "-e", script)
	if err != nil {
		return nil, fmt.Errorf("chrome tabs unavailable: %v", err)
	}
	var tabs []ChromeTabInfo
	scanner := bufio.NewScanner(bytes.NewReader(output))
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		fields := strings.SplitN(line, "|||", 4)
		if len(fields) < 4 {
			continue
		}
		windowIndex, _ := strconv.Atoi(fields[0])
		tabIndex, _ := strconv.Atoi(fields[1])
		tabs = append(tabs, ChromeTabInfo{Window: windowIndex, Index: tabIndex, Title: fields[2], URL: fields[3]})
	}
	return tabs, scanner.Err()
}

func CollectSummary(procs []ProcessInfo, ports []PortInfo, groups []GroupInfo) SummaryInfo {
	return SummaryInfo{
		LoadAvg:   LoadAverage(),
		CPUUsage:  CpuUsage(),
		Memory:    MemorySummary(),
		Disk:      DiskSummary(),
		ProcCount: len(procs),
		PortCount: len(ports),
		TopGroups: TopGroups(groups),
	}
}

func ExportSnapshot(snap Snapshot, dir string) (ExportResult, error) {
	if dir == "" {
		dir = filepath.Join(".", "resource-snapshots")
	}
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return ExportResult{}, err
	}
	timestamp := snap.CollectedAt.Format("20060102-150405")
	jsonPath := filepath.Join(dir, "resource-snapshot-"+timestamp+".json")
	mdPath := filepath.Join(dir, "resource-snapshot-"+timestamp+".md")

	jsonBytes, err := json.MarshalIndent(snap, "", "  ")
	if err != nil {
		return ExportResult{}, err
	}
	if err := os.WriteFile(jsonPath, append(jsonBytes, '\n'), 0o644); err != nil {
		return ExportResult{}, err
	}
	if err := os.WriteFile(mdPath, []byte(RenderMarkdownSnapshot(snap)), 0o644); err != nil {
		return ExportResult{}, err
	}
	return ExportResult{JSONPath: jsonPath, MarkdownPath: mdPath}, nil
}

func RenderMarkdownSnapshot(snap Snapshot) string {
	var b strings.Builder
	b.WriteString("# Resource Snapshot\n\n")
	b.WriteString(fmt.Sprintf("Collected: %s\n\n", snap.CollectedAt.Format("2006-01-02 15:04:05")))
	b.WriteString("## Summary\n\n")
	b.WriteString(fmt.Sprintf("- Load: %s\n", snap.Summary.LoadAvg))
	b.WriteString(fmt.Sprintf("- CPU: %s\n", snap.Summary.CPUUsage))
	b.WriteString(fmt.Sprintf("- Memory: %s\n", snap.Summary.Memory))
	b.WriteString(fmt.Sprintf("- Disk: %s\n", snap.Summary.Disk))
	b.WriteString(fmt.Sprintf("- Processes: %d\n", snap.Summary.ProcCount))
	b.WriteString(fmt.Sprintf("- Ports: %d\n", snap.Summary.PortCount))
	if len(snap.Errs) > 0 {
		b.WriteString(fmt.Sprintf("- Collection warnings: %s\n", strings.Join(snap.Errs, " | ")))
	}
	b.WriteString("\n")

	b.WriteString("## Process Groups by CPU\n\n")
	b.WriteString("| Group | CPU % | RSS MiB | Procs | Ports | Top PIDs |\n")
	b.WriteString("|---|---:|---:|---:|---|---|\n")
	groups := append([]GroupInfo(nil), snap.Groups...)
	sort.SliceStable(groups, func(i, j int) bool { return groups[i].CPU > groups[j].CPU })
	for _, group := range firstGroups(groups, 12) {
		b.WriteString(fmt.Sprintf("| %s | %.1f | %.1f | %d | %s | %s |\n", mdEscape(group.Name), group.CPU, float64(group.RSSKiB)/1024, group.Count, mdEscape(IntList(group.Ports, 12)), mdEscape(IntList(group.TopPIDs, 8))))
	}
	b.WriteString("\n")

	b.WriteString("## Process Groups by Memory\n\n")
	b.WriteString("| Group | RSS MiB | CPU % | Procs | Ports | Top PIDs |\n")
	b.WriteString("|---|---:|---:|---:|---|---|\n")
	sort.SliceStable(groups, func(i, j int) bool { return groups[i].RSSKiB > groups[j].RSSKiB })
	for _, group := range firstGroups(groups, 12) {
		b.WriteString(fmt.Sprintf("| %s | %.1f | %.1f | %d | %s | %s |\n", mdEscape(group.Name), float64(group.RSSKiB)/1024, group.CPU, group.Count, mdEscape(IntList(group.Ports, 12)), mdEscape(IntList(group.TopPIDs, 8))))
	}
	b.WriteString("\n")

	b.WriteString("## Top CPU Processes\n\n")
	b.WriteString("| PID | CPU % | RSS MiB | Group | Ports | Command |\n")
	b.WriteString("|---:|---:|---:|---|---|---|\n")
	processes := append([]ProcessInfo(nil), snap.Processes...)
	sort.SliceStable(processes, func(i, j int) bool { return processes[i].CPU > processes[j].CPU })
	for _, proc := range firstProcesses(processes, 20) {
		b.WriteString(fmt.Sprintf("| %d | %.1f | %.1f | %s | %s | `%s` |\n", proc.PID, proc.CPU, float64(proc.RSSKiB)/1024, mdEscape(proc.Group), mdEscape(PortList(proc.Ports)), mdEscape(ShortenForPrint(proc.Command, 140))))
	}
	b.WriteString("\n")

	b.WriteString("## Top Memory Processes\n\n")
	b.WriteString("| PID | CPU % | RSS MiB | Group | Ports | Command |\n")
	b.WriteString("|---:|---:|---:|---|---|---|\n")
	sort.SliceStable(processes, func(i, j int) bool { return processes[i].RSSKiB > processes[j].RSSKiB })
	for _, proc := range firstProcesses(processes, 20) {
		b.WriteString(fmt.Sprintf("| %d | %.1f | %.1f | %s | %s | `%s` |\n", proc.PID, proc.CPU, float64(proc.RSSKiB)/1024, mdEscape(proc.Group), mdEscape(PortList(proc.Ports)), mdEscape(ShortenForPrint(proc.Command, 140))))
	}
	b.WriteString("\n")

	b.WriteString("## Ports / Sockets\n\n")
	b.WriteString("| Port | Protocol | PID | Command | Address |\n")
	b.WriteString("|---:|---|---:|---|---|\n")
	ports := append([]PortInfo(nil), snap.Ports...)
	sort.SliceStable(ports, func(i, j int) bool { return ports[i].Port < ports[j].Port })
	for _, port := range firstPorts(ports, 80) {
		b.WriteString(fmt.Sprintf("| %d | %s | %d | %s | `%s` |\n", port.Port, mdEscape(port.Protocol), port.PID, mdEscape(port.Command), mdEscape(port.Address)))
	}
	b.WriteString("\n")

	b.WriteString("## Chrome Tabs\n\n")
	b.WriteString("Chrome tab titles and URLs are collected through AppleScript. They are useful clues, but macOS/Chrome does not expose a reliable public mapping from Renderer PID to a specific tab. Treat PID-to-tab attribution as inference unless confirmed in Chrome Task Manager.\n\n")
	if len(snap.ChromeTabs) == 0 {
		b.WriteString("No Chrome tabs were available, or Chrome automation permission was not granted.\n")
	} else {
		b.WriteString("| Window | Tab | Title | URL |\n")
		b.WriteString("|---:|---:|---|---|\n")
		for _, tab := range snap.ChromeTabs {
			b.WriteString(fmt.Sprintf("| %d | %d | %s | %s |\n", tab.Window, tab.Index, mdEscape(tab.Title), mdEscape(tab.URL)))
		}
	}
	b.WriteString("\n")

	b.WriteString("## Suggested AI Prompt\n\n")
	b.WriteString("Use this snapshot to identify the likely causes of resource pressure. Prioritize: sustained high CPU processes, high RSS processes, multi-process app groups, suspicious listening ports, and Chrome tab clues. Explain what to close, restart, or inspect next, and call out any uncertainty.\n")
	return b.String()
}

func RunCommand(timeout time.Duration, name string, args ...string) ([]byte, error) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	cmd := exec.CommandContext(ctx, name, args...)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	output, err := cmd.Output()
	if ctx.Err() == context.DeadlineExceeded {
		return output, fmt.Errorf("%s timed out", name)
	}
	if err != nil && stderr.Len() > 0 {
		return output, fmt.Errorf("%s: %s", name, strings.TrimSpace(stderr.String()))
	}
	return output, err
}

func LoadAverage() string {
	output, err := RunCommand(2*time.Second, "uptime")
	if err != nil {
		return "unknown"
	}
	text := strings.TrimSpace(string(output))
	idx := strings.Index(text, "load averages:")
	if idx < 0 {
		idx = strings.Index(text, "load average:")
	}
	if idx >= 0 {
		return strings.TrimSpace(text[idx+len("load averages:"):])
	}
	return text
}

func CpuUsage() string {
	output, err := RunCommand(8*time.Second, "top", "-l", "1", "-n", "0", "-s", "0")
	if err != nil && len(output) == 0 {
		return "unknown"
	}
	re := regexp.MustCompile(`CPU usage:\s+([\d.]+)% user,\s+([\d.]+)% sys,\s+([\d.]+)% idle`)
	match := re.FindStringSubmatch(string(output))
	if len(match) != 4 {
		return "unknown"
	}
	user, _ := strconv.ParseFloat(match[1], 64)
	sys, _ := strconv.ParseFloat(match[2], 64)
	idle, _ := strconv.ParseFloat(match[3], 64)
	return fmt.Sprintf("used %.1f%%, user %.1f%%, sys %.1f%%, idle %.1f%%", 100-idle, user, sys, idle)
}

func MemorySummary() string {
	memBytes := SysctlInt("hw.memsize")
	output, err := RunCommand(2*time.Second, "vm_stat")
	if err != nil {
		return "unknown"
	}
	pageSize := 4096
	pageRe := regexp.MustCompile(`page size of\s+(\d+)\s+bytes`)
	if match := pageRe.FindStringSubmatch(string(output)); len(match) == 2 {
		pageSize, _ = strconv.Atoi(match[1])
	}
	pages := make(map[string]int)
	labels := map[string]string{
		"Pages free":                    "free",
		"Pages speculative":             "speculative",
		"Pages purgeable":              "purgeable",
		"Pages occupied by compressor":  "compressed",
	}
	scanner := bufio.NewScanner(bytes.NewReader(output))
	for scanner.Scan() {
		line := scanner.Text()
		for label, key := range labels {
			if strings.HasPrefix(line, label) {
				raw := regexp.MustCompile(`[^0-9]`).ReplaceAllString(strings.SplitN(line, ":", 2)[1], "")
				pages[key], _ = strconv.Atoi(raw)
			}
		}
	}
	available := float64(pages["free"]+pages["speculative"]+pages["purgeable"]) * float64(pageSize) / (1024 * 1024 * 1024)
	compressed := float64(pages["compressed"]) * float64(pageSize) / (1024 * 1024 * 1024)
	total := float64(memBytes) / (1024 * 1024 * 1024)
	used := total - available
	return fmt.Sprintf("used-ish %.2f/%.2f GiB, available %.2f GiB, compressed %.2f GiB", used, total, available, compressed)
}

func DiskSummary() string {
	output, err := RunCommand(2*time.Second, "df", "-h", "/", "/System/Volumes/Data")
	if err != nil {
		return "unknown"
	}
	seen := make(map[string]bool)
	parts := make([]string, 0, 2)
	scanner := bufio.NewScanner(bytes.NewReader(output))
	first := true
	for scanner.Scan() {
		line := scanner.Text()
		if first {
			first = false
			continue
		}
		fields := strings.Fields(line)
		if len(fields) < 9 {
			continue
		}
		mount := fields[len(fields)-1]
		if seen[mount] {
			continue
		}
		seen[mount] = true
		parts = append(parts, fmt.Sprintf("%s %s used, %s free", mount, fields[4], fields[3]))
	}
	return strings.Join(parts, " | ")
}

func SysctlInt(name string) int64 {
	output, err := RunCommand(2*time.Second, "sysctl", "-n", name)
	if err != nil {
		return 0
	}
	value, _ := strconv.ParseInt(strings.TrimSpace(string(output)), 10, 64)
	return value
}

func AggregateGroups(procs []ProcessInfo) []GroupInfo {
	groups := map[string]*GroupInfo{}
	members := map[string][]ProcessInfo{}
	portSets := map[string]map[int]bool{}
	for _, proc := range procs {
		name := proc.Group
		if name == "" {
			name = ProcessGroup(proc.Command)
		}
		group := groups[name]
		if group == nil {
			group = &GroupInfo{Name: name}
			groups[name] = group
			portSets[name] = make(map[int]bool)
		}
		group.CPU += proc.CPU
		group.RSSKiB += proc.RSSKiB
		group.Count++
		members[name] = append(members[name], proc)
		for _, port := range proc.Ports {
			portSets[name][port.Port] = true
		}
	}
	items := make([]GroupInfo, 0, len(groups))
	for name, group := range groups {
		for port := range portSets[name] {
			group.Ports = append(group.Ports, port)
		}
		sort.Ints(group.Ports)
		procs := members[name]
		sort.SliceStable(procs, func(i, j int) bool { return procs[i].CPU > procs[j].CPU })
		for i, proc := range procs {
			if i >= 5 {
				break
			}
			group.TopPIDs = append(group.TopPIDs, proc.PID)
			group.TopCommands = append(group.TopCommands, fmt.Sprintf("%d %.1f%% %s", proc.PID, proc.CPU, ShortenForPrint(proc.Command, 56)))
		}
		items = append(items, *group)
	}
	sort.SliceStable(items, func(i, j int) bool { return items[i].CPU > items[j].CPU })
	return items
}

func TopGroups(groups []GroupInfo) string {
	pieces := make([]string, 0, 4)
	for _, item := range groups {
		if item.Name == "Other" && len(pieces) > 0 {
			continue
		}
		pieces = append(pieces, fmt.Sprintf("%s %.0f%% %.0fMiB", item.Name, item.CPU, float64(item.RSSKiB)/1024))
		if len(pieces) == 4 {
			break
		}
	}
	return strings.Join(pieces, " | ")
}

func ProcessGroup(command string) string {
	for _, rule := range groupRules {
		if rule.re.MatchString(command) {
			return rule.name
		}
	}
	return "Other"
}

func ParsePort(address string) int {
	local := address
	if strings.Contains(address, "->") {
		local = strings.SplitN(address, "->", 2)[0]
	}
	matches := portPattern.FindAllStringSubmatch(local, -1)
	if len(matches) == 0 {
		return 0
	}
	port, _ := strconv.Atoi(matches[len(matches)-1][1])
	return port
}

func FirstPort(ports []PortInfo) int {
	if len(ports) == 0 {
		return 0
	}
	min := ports[0].Port
	for _, port := range ports[1:] {
		if port.Port < min {
			min = port.Port
		}
	}
	return min
}

func PortList(ports []PortInfo) string {
	if len(ports) == 0 {
		return ""
	}
	values := make([]string, 0, len(ports))
	for _, port := range ports {
		values = append(values, strconv.Itoa(port.Port))
	}
	sort.Strings(values)
	if len(values) > 5 {
		return strings.Join(values[:5], ",") + ",..."
	}
	return strings.Join(values, ",")
}

func IntList(values []int, limit int) string {
	if len(values) == 0 {
		return ""
	}
	copyValues := append([]int(nil), values...)
	sort.Ints(copyValues)
	if limit > 0 && len(copyValues) > limit {
		copyValues = copyValues[:limit]
	}
	parts := make([]string, 0, len(copyValues))
	for _, value := range copyValues {
		parts = append(parts, strconv.Itoa(value))
	}
	if limit > 0 && len(values) > limit {
		parts = append(parts, "...")
	}
	return strings.Join(parts, ",")
}

func firstInt(values []int) int {
	if len(values) == 0 {
		return 0
	}
	min := values[0]
	for _, value := range values[1:] {
		if value < min {
			min = value
		}
	}
	return min
}

func firstProcesses(processes []ProcessInfo, limit int) []ProcessInfo {
	if len(processes) <= limit {
		return processes
	}
	return processes[:limit]
}

func firstPorts(ports []PortInfo, limit int) []PortInfo {
	if len(ports) <= limit {
		return ports
	}
	return ports[:limit]
}

func firstGroups(groups []GroupInfo, limit int) []GroupInfo {
	if len(groups) <= limit {
		return groups
	}
	return groups[:limit]
}

func ShortenForPrint(text string, limit int) string {
	text = strings.Join(strings.Fields(text), " ")
	if len(text) <= limit {
		return text
	}
	if limit <= 3 {
		return text[:limit]
	}
	return text[:limit-3] + "..."
}

func mdEscape(text string) string {
	text = strings.ReplaceAll(text, "|", "\\|")
	text = strings.ReplaceAll(text, "\n", " ")
	text = strings.ReplaceAll(text, "`", "'")
	return text
}

func CompareInt(left, right int) int {
	if left < right {
		return -1
	}
	if left > right {
		return 1
	}
	return 0
}

func CompareFloat(left, right float64) int {
	if left < right {
		return -1
	}
	if left > right {
		return 1
	}
	return 0
}

func FindProcess(processes []ProcessInfo, pid int) *ProcessInfo {
	for i := range processes {
		if processes[i].PID == pid {
			return &processes[i]
		}
	}
	return nil
}