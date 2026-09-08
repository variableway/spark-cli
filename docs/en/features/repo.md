# Repository Management

## Overview

`spark repo` manages multiple GitHub repositories under a directory via a registry file, as an alternative to submodules. Use it when a directory contains many GitHub repositories that you do not want to manage as submodules.

## Core Capabilities

### Directory Scanning

Recursively scan a directory for Git repositories with an `origin` remote and write them to `registry_<folder>.yaml`.

```bash
spark repo scan ~/workspace/innate-apps
```

- Skips hidden directories and `node_modules`/`venv`/`.venv`/`__pycache__`/`dist`/`build`
- Normalizes SSH URLs to HTTPS form before storing
- Re-scanning merges with the existing registry, preserving `name`/`desc` and removing vanished entries

### Batch Cloning

Clone repositories from a registry file into the folder directory, either all at once or by name.

```bash
# Clone everything
spark repo clone -f registry_innate-apps.yaml

# Clone only the named repository
spark repo clone -r spark-cli -f registry_innate-apps.yaml
```

Repositories that already exist are skipped automatically.

### Listing Repositories

List the repositories declared in a registry file.

```bash
spark repo list -f registry_innate-apps.yaml
```

## Registry file

```yaml
# Project registry
# Synced by spark repo scan

projects:
    - name: spark-cli
      repo: https://github.com/variableway/spark-cli.git
      path: tooling/spark-cli
      desc: Spark CLI tool
```

## Dependencies

- The `git` command-line tool

## Related

- [Repo Command Spec](/en/spec/repo)
- [Repo Usage Guide](/en/usage/repo)
