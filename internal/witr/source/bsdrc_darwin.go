//go:build darwin

package source

import "spark/pkg/witr/model"

func detectBsdRc(_ []model.Process) *model.Source {
	// macOS doesn't use FreeBSD rc.d
	return nil
}
