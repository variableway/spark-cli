package hub

import (
	"github.com/spf13/cobra"
)

var RegistryCmd = &cobra.Command{
	Use:   "registry",
	Short: "Manage a references directory with a registry file",
	Long: `Registry tracks reference repositories in registry_<folder>.yaml so a
directory can be scanned and cloned without git submodules.

This is not the collections catalog. Collections registers apps you develop;
registry restores the references tree.`,
}

var CollectionsCmd = &cobra.Command{
	Use:   "collections",
	Short: "Register apps you develop into an innate-apps collections catalog",
	Long: `Collections scans local app repositories and writes registry/apps.json.
Merge keeps curated fields (title, category, status, url, description).

This catalog is separate from the references registry used by hub registry.`,
}

var HubCmd = &cobra.Command{
	Use:   "hub",
	Short: "Registry for references, collections for apps you develop",
	Long: `Hub has two registries because they are used differently.

registry    — a references directory. Scan writes registry_<folder>.yaml;
              list and clone restore that tree.
collections — apps you develop. Scan writes the innate-apps collections
              catalog (registry/apps.json).`,
}

func init() {
	HubCmd.AddCommand(RegistryCmd, CollectionsCmd)
	RegistryCmd.AddCommand(scanCmd, listCmd, cloneCmd, cloneRegistryCmd)
	CollectionsCmd.AddCommand(registerCmd)
}
