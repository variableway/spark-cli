# Makefile for Spark

BINARY_NAME=spark
GO=go
GINKGO=$(GO) run github.com/onsi/ginkgo/v2/ginkgo

# Detect OS
ifeq ($(OS),Windows_NT)
    BINARY_EXT=.exe
    RM=if exist $(BINARY_NAME)$(BINARY_EXT) del $(BINARY_NAME)$(BINARY_EXT)
else
    BINARY_EXT=
    RM=rm -f $(BINARY_NAME)$(BINARY_EXT)
endif

.PHONY: all build build-linux build-darwin test test-bdd clean lint help

all: build test

build:
	$(GO) build -o $(BINARY_NAME)$(BINARY_EXT) main.go

build-linux:
	GOOS=linux GOARCH=amd64 $(GO) build -o $(BINARY_NAME)_linux main.go

build-darwin:
	GOOS=darwin GOARCH=amd64 $(GO) build -o $(BINARY_NAME)_darwin main.go

test:
	$(GO) test ./... -v

test-bdd:
	$(GINKGO) -v ./internal/...

lint:
	$(GO) vet ./...

clean:
	$(RM)
	$(GO) clean

help:
	@echo "Available targets:"
	@echo "  build         - Build for current OS"
	@echo "  build-linux   - Cross-compile for Linux (amd64)"
	@echo "  build-darwin  - Cross-compile for macOS (amd64)"
	@echo "  test          - Run all tests"
	@echo "  test-bdd      - Run tests with BDD output"
	@echo "  lint          - Run go vet"
	@echo "  clean         - Remove binary and build artifacts"
