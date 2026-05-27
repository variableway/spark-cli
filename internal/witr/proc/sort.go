package proc

import (
	"sort"

	"spark/pkg/witr/model"
)

func sortProcesses(processes []model.Process) {
	sort.Slice(processes, func(i, j int) bool {
		return processes[i].PID < processes[j].PID
	})
}
