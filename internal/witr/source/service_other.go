//go:build !windows

package source

import "spark/pkg/witr/model"

func detectWindowsService(ancestry []model.Process) *model.Source {
	return nil
}
