//go:build windows

package proc

import "spark/pkg/witr/model"

func GetFileContext(pid int) *model.FileContext {
	return nil
}
