// Package templates provides embedded template files bundled into the Spark binary.
// These templates can be deployed to a target machine via `spark magic copy-config`.
package templates

import "embed"

//go:embed dotfiles
var Dotfiles embed.FS
