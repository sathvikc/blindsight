# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — 2026-07-18

### Added

- **Plugin system**: Third-party packages can now register extraction modules via Python entry points (`blindsight.modules` group). Plugins are opt-in and append after built-in modules, enabling extensibility without modifying core code.
- **Installation path documentation**: Added pipx-based install option as the lead method for running Blindsight from any directory.

### Changed

- **Documentation**: Clarified README install/MCP setup sections to better distinguish setup paths.

### Internal

- Added release and PR templates for contribution workflow.
- Set up Graphify knowledge graph for codebase navigation (474 nodes, 21 communities).

## [0.2.0] — Previous release

Initial stable release with core extraction modules and CLI/MCP server support.
