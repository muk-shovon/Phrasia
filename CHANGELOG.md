# Changelog

All notable changes to Phrasia are recorded here. This file follows the categories from [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Deterministic humanizer skill pass with a shared 26-section catalog, tiered edits, review signals, and fixture coverage.
- First-run Python bootstrap, public contribution guide, GitHub templates, cross-platform CI, and MIT license.
- Committed frontend bundle so end users need only Python.

### Changed

- Reworked the backend around the Python-only rule engine, validators, ranker, local style scanner, and local SQLite repository.
- Updated the Humanizer report and review interface, launcher, dependency ranges, and public documentation.
- Separated runtime and development Python dependencies.

### Removed

- Duplicate style matching and obsolete provider-era launcher behavior.
- Generated environments, caches, local databases, and machine-specific files from the current Git index.

## 2026-11-24 — Local app and frontend refactor

### Added

- FastAPI backend with a Vite and TypeScript frontend.
- Local plagiarism reference workflow, document history, style-signal page, and text/DOCX export.
- Two-column Humanizer interface, diff review, accessibility improvements, and the current visual design.

### Changed

- Replaced the earlier UI and cloud-oriented storage structure with local browser pages and SQLite persistence.
- Consolidated API routes and page modules around the local application.

## 2026-11-23 — Initial repository

### Added

- Initial Phrasia application and repository structure.
