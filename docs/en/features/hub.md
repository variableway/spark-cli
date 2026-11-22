# Project Hub

## Overview

`spark hub` is the entry point for scanning, registering, and cloning from a list. It keeps two lists because they are used differently:

- **registry** manages a references directory. Scan writes `registry_<folder>.yaml`, and clone restores the repositories from that file.
- **collections** registers apps you develop. Scan writes `registry/apps.json` for the docs site and profile.

A directory of repositories uses registry, not git submodules.

## Core Capabilities

### References: scan and clone

```bash
spark hub registry scan ~/workspace/innate-references
spark hub registry clone -f registry_innate-references.yaml
spark hub registry clone-registry registry_references.yaml --dry-run
```

A rescan merges. Entries that are not checked out stay in the file and can be restored later with `clone` or `clone-registry`.

### Apps you develop: write collections

```bash
spark hub collections scan . -o registry/apps.json --merge registry/apps.json
```

Merging keeps hand-maintained `title` / `category` / `status` / `url` / `description`.

## Related

- [Hub command spec](../spec/hub.md)
- [Hub usage](../usage/hub.md)
