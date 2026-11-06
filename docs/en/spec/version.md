# spark version — Command Spec

Print the spark binary version, source commit, and build date. Useful for confirming that the spark binary on PATH matches the latest source build.

## Parent

```
spark version
```

No arguments, no flags.

---

## spark version

```
spark version [flags]
```

| Flag | Short | Type | Default | Required | Description |
|------|-------|------|---------|----------|-------------|
| `--help` | `-h` | bool | `false` | No | Show help |

No arguments.

---

## spark --version

The root command carries a version flag that prints the short form of the version information.

| Flag | Short | Type | Default | Required | Description |
|------|-------|------|---------|----------|-------------|
| `--version` | `-v` | bool | `false` | No | Print the spark version |

---

## Output Formats

`spark version` prints the version, the commit hash, the build date, and the VCS time from the build information:

```
spark v0.3.3
  commit:     25d5128
  build date: 2026-11-01T04:26:58Z
  vcs.time:   2026-11-01T04:26:58Z (dirty)
```

- The first line is `spark` followed by the version.
- `commit` is the short hash of the source commit.
- `build date` is the build time in UTC.
- `vcs.time` comes from the Go build information (`debug.ReadBuildInfo()`) and is only printed when that field is present. When the build information has no `vcs.time` but does have `vcs.revision`, this line prints the first 7 characters of the commit hash instead.
- The `(dirty)` suffix means the working tree had uncommitted changes at build time; it only appears when `vcs.modified` is `true`.

`spark --version` prints the short form:

```
spark version v0.3.3
```

---

## Where the Version Comes From

The version is injected at build time, not computed at runtime.

The version literal lives in the `internal/witr/version/VERSION` file, whose content is:

```
0.3.3
```

The `Makefile` reads that file at build time and injects the version, commit hash, and build date into the variables of the `spark/internal/witr/version` package via `-ldflags`:

```
VERSION ?= $(shell cat internal/witr/version/VERSION 2>/dev/null || echo dev)
COMMIT  ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)
DATE    ?= $(shell date -u +%Y-%m-%dT%H:%M:%SZ)
LDFLAGS := -s -w \
    -X "spark/internal/witr/version.Version=v$(VERSION)" \
    -X "spark/internal/witr/version.Commit=$(COMMIT)" \
    -X "spark/internal/witr/version.BuildDate=$(DATE)"
```

The build task in `Taskfile.yml` uses the same three variables and the same injection.

When no `-ldflags` are supplied (for example Debian packaging or `go install`), `internal/witr/version/version.go` falls back to the embedded VERSION file and the VCS build information:

- The version comes from the file embedded via `//go:embed VERSION`, with a `v` prefix added
- The commit hash comes from the first 7 characters of `vcs.revision`
- The build date comes from `vcs.time`
- If any of them is still empty, they fall back to `v0.0.0-dev`, `unknown`, and `unknown` respectively

---

## Related Docs

- [Command Overview](../usage/usage.md)
- [Witr Usage Guide](../usage/witr.md)
