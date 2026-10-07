# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a KKT validity checker for Russian fiscal devices. The project validates KKT devices against the official Russian tax service registry at `https://kkt-online.nalog.ru`.

## Development Commands

```bash
# Install dependencies using uv (modern Python package manager)
uv sync

# Run linting and formatting (configured in pyproject.toml)
ruff check .
ruff format .

# Run the main application
python main.py
```

## Architecture

The project consists of two main modules:

### KKTClient (`client.py:15-41`)
HTTP client wrapper for the Russian tax service KKT registry API. Handles:
- Model retrieval from the registry
- Individual KKT instance validation
- Base URL: `https://kkt-online.nalog.ru`

### KKTChecker (`client.py:43-119`)
Business logic layer that:
- Normalizes text input (removes non-alphanumeric, lowercases)
- Maps model names to registry codes
- Handles retry logic for timeout errors (max 5 attempts)
- Returns structured results: SUCCESS, FAILED, or ERROR

### Excel Processing (`main.py`)
Main script that processes Excel files (`test.xlsx`) with KKT data:
- Reads from "ККТ" worksheet
- Expected columns: "Наименование", "Модель ККТ", "Заводской Номер ККТ", "Статус Проверки"
- Color-codes results: green (success), red (failed), yellow (error)
- Processes up to 400 rows with 0.5-second delays between API calls

## Code Style

- Line length: 120 characters
- Ruff configuration includes extended linting rules (I, PTH, B, A, N, PT, COM, E, W, UP)
- Double quotes for strings
- Docstring code formatting enabled
