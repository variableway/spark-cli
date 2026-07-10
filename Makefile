BINARY_NAME=spark
GO=go
GINKGO=$(GO) run github.com/onsi/ginkgo/v2/ginkgo

# Install directory
INSTALL_DIR=~/.local/bin

# Detect OS
ifeq ($(OS),Windows_NT)
    BINARY_EXT=.exe
    RM=if exist $(BINARY_NAME)$(BINARY_EXT) del $(BINARY_NAME)$(BINARY_EXT)
else
    BINARY_EXT=
    RM=rm -f $(BINARY_NAME)$(BINARY_EXT)
endif

.PHONY: all build build-linux build-darwin test test-bdd clean lint help verify-install

all: build test

VERSION ?= $(shell cat internal/witr/version/VERSION 2>/dev/null || echo dev)
COMMIT  ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)
DATE    ?= $(shell date -u +%Y-%m-%dT%H:%M:%SZ)
LDFLAGS := -s -w \
    -X "spark/internal/witr/version.Version=v$(VERSION)" \
    -X "spark/internal/witr/version.Commit=$(COMMIT)" \
    -X "spark/internal/witr/version.BuildDate=$(DATE)"

build: clean
	@MACOSX_DEPLOYMENT_TARGET_VAL=$$(sw_vers -productVersion 2>/dev/null || echo "15.0"); \
	MACOSX_DEPLOYMENT_TARGET=$$MACOSX_DEPLOYMENT_TARGET_VAL \
	CGO_CFLAGS="-mmacosx-version-min=$$MACOSX_DEPLOYMENT_TARGET_VAL" \
	CGO_LDFLAGS="-mmacosx-version-min=$$MACOSX_DEPLOYMENT_TARGET_VAL" \
	$(GO) build -ldflags='$(LDFLAGS)' -o $(BINARY_NAME)$(BINARY_EXT) main.go
	@echo "Installing $(BINARY_NAME) to $(INSTALL_DIR)..."
	@mkdir -p $(INSTALL_DIR)
ifeq ($(OS),Windows_NT)
	@# On Windows keep both .exe and extension-less copies in sync; bash matches
	@# the latter first when both exist in PATH, so they must match.
	@cp $(BINARY_NAME)$(BINARY_EXT) $(INSTALL_DIR)/$(BINARY_NAME)$(BINARY_EXT)
	@cp $(BINARY_NAME)$(BINARY_EXT) $(INSTALL_DIR)/$(BINARY_NAME)
else
	@cp $(BINARY_NAME)$(BINARY_EXT) $(INSTALL_DIR)/$(BINARY_NAME)$(BINARY_EXT)
endif
	@$(MAKE) -s verify-install

build-linux:
	GOOS=linux GOARCH=amd64 $(GO) build -ldflags='$(LDFLAGS)' -o $(BINARY_NAME)_linux main.go

build-darwin:
	@MACOSX_DEPLOYMENT_TARGET_VAL=$$(sw_vers -productVersion 2>/dev/null || echo "15.0"); \
	MACOSX_DEPLOYMENT_TARGET=$$MACOSX_DEPLOYMENT_TARGET_VAL \
	CGO_CFLAGS="-mmacosx-version-min=$$MACOSX_DEPLOYMENT_TARGET_VAL" \
	CGO_LDFLAGS="-mmacosx-version-min=$$MACOSX_DEPLOYMENT_TARGET_VAL" \
	GOOS=darwin GOARCH=amd64 $(GO) build -ldflags='$(LDFLAGS)' -o $(BINARY_NAME)_darwin main.go

test:
	$(GO) test ./... -v

test-bdd:
	$(GINKGO) -v ./internal/...

lint:
	$(GO) vet ./...

install: build

install-only:
	@echo "Installing $(BINARY_NAME) to $(INSTALL_DIR)..."
	@mkdir -p $(INSTALL_DIR)
ifeq ($(OS),Windows_NT)
	@cp $(BINARY_NAME)$(BINARY_EXT) $(INSTALL_DIR)/$(BINARY_NAME)$(BINARY_EXT)
	@cp $(BINARY_NAME)$(BINARY_EXT) $(INSTALL_DIR)/$(BINARY_NAME)
else
	@cp $(BINARY_NAME)$(BINARY_EXT) $(INSTALL_DIR)/$(BINARY_NAME)$(BINARY_EXT)
endif
	@$(MAKE) -s verify-install

verify-install:
	@echo ""
	@echo "Install verification:"
	@ls -la $(BINARY_NAME)$(BINARY_EXT) 2>/dev/null | awk '{printf "  src: %s  (%s bytes, %s %s)\n", $$NF, $$5, $$6, $$7" "$$8}'
	@ls -la $(INSTALL_DIR)/$(BINARY_NAME)$(BINARY_EXT) 2>/dev/null | awk '{printf "  dst: %s  (%s bytes, %s %s)\n", $$9, $$5, $$6, $$7" "$$8}'
ifeq ($(OS),Windows_NT)
	@ls -la $(INSTALL_DIR)/$(BINARY_NAME) 2>/dev/null | awk '{printf "  dst: %s  (%s bytes, %s %s)\n", $$9, $$5, $$6, $$7" "$$8}'
endif
	@SRC_HASH=$$(sha256sum $(BINARY_NAME)$(BINARY_EXT) 2>/dev/null | cut -d' ' -f1); \
	DST_HASH=$$(sha256sum $(INSTALL_DIR)/$(BINARY_NAME)$(BINARY_EXT) 2>/dev/null | cut -d' ' -f1); \
	if [ "$$SRC_HASH" = "$$DST_HASH" ] && [ -n "$$SRC_HASH" ]; then \
		echo "  sha256 matches: $$SRC_HASH"; \
	else \
		echo "  HASH MISMATCH: src=$$SRC_HASH dst=$$DST_HASH"; \
	fi

clean:
	$(RM)
	$(GO) clean

help:
	@echo "Available targets:"
	@echo "  build         - Build for current OS, stamp version, install to $(INSTALL_DIR)"
	@echo "  install       - Same as build (build + install)"
	@echo "  install-only  - Install existing binary without rebuilding"
	@echo "  verify-install- Compare installed binary sha256 against source"
	@echo "  build-linux   - Cross-compile for Linux (amd64)"
	@echo "  build-darwin  - Cross-compile for macOS (amd64)"
	@echo "  test          - Run all tests"
	@echo "  test-bdd      - Run tests with BDD output"
	@echo "  lint          - Run go vet"
	@echo "  clean         - Remove binary and build artifacts"
