# KKT Checker

A tool for validating KKT (cash register) devices against the official Russian Federal Tax Service registry.

## Features

- Validate KKT instances via the `kkt-online.nalog.ru` API
- Batch validation from Excel files with color-coded results
- Telegram bot for interactive validation
- Automatic retries on timeout errors

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (package manager)

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd ksp

# Install dependencies
uv sync
```

## Usage

### Excel Processing

Place a `test.xlsx` file with a worksheet named "ККТ" in the project root. Expected columns:

| Column | Description |
|--------|-------------|
| Наименование | Organization name |
| Модель ККТ | Cash register model |
| Заводской Номер ККТ | Device serial number |
| Статус Проверки | Result (filled automatically) |

```bash
python main.py
```

Results are written to the same file with color coding:
- Green — validation successful
- Red — validation failed
- Yellow — validation error

### Telegram Bot

1. Create a `.env` file:

```env
BOT_TOKEN=your_telegram_bot_token
```

2. Start the bot:

```bash
python bot_main.py
```

#### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BOT_TOKEN` | — | Telegram bot token (required) |
| `TEMP_DIR` | `temp` | Directory for temporary files |
| `MAX_FILE_SIZE_MB` | `10` | Maximum upload file size |
| `MAX_CONCURRENT_CHECKS` | `5` | Number of parallel checks |
| `API_DELAY_SECONDS` | `0.5` | Delay between API requests |
| `MAX_RETRIES` | `5` | Maximum retry attempts |
| `RETRY_DELAY_SECONDS` | `10` | Delay before retry |

## Project Structure

```
ksp/
├── client.py      # HTTP client and KKT validation logic
├── config.py      # Application configuration
├── main.py        # Excel file processing
├── bot_main.py    # Telegram bot entry point
└── bot/           # Telegram bot module
    ├── handlers.py
    └── utils.py
```

## Development

```bash
# Linting
ruff check .

# Formatting
ruff format .
```
