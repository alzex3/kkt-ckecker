# Deployment Guide

## Remote Host Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd kkt
```

### 2. Environment Configuration
```bash
cp .env.example .env
# Edit .env and set your BOT_TOKEN
nano .env
```

### 3. Deploy with Docker Compose
```bash
# Build and start the bot
docker compose up -d

# View logs
docker compose logs -f kkt-bot

# Stop the bot
docker compose down
```

### 4. Auto-start on System Reboot

The bot will automatically restart with the system because:
- Docker service starts on boot (default behavior)
- Container has `restart: always` policy in docker-compose.yml

To ensure Docker starts on boot:
```bash
sudo systemctl enable docker
```

### 5. Management Commands
```bash
# Restart the bot
docker compose restart kkt-bot

# Update and redeploy
git pull
docker compose up -d --build

# View container status
docker compose ps

# View resource usage
docker stats kkt-telegram-bot
```

## Troubleshooting

### Bot not starting
- Check BOT_TOKEN in .env file
- Verify Docker is running: `sudo systemctl status docker`
- Check logs: `docker compose logs kkt-bot`

### Container keeps restarting
- Check bot.pid file conflicts
- Verify network connectivity to Telegram API
- Check available disk space in temp/ directory