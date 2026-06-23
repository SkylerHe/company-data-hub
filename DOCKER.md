# Docker Setup Guide (OrbStack)

Run the entire Company Data Hub in Docker containers - perfect for OrbStack users!

## Why Docker?

✅ **No Python setup needed** - Everything runs in containers
✅ **Always running** - Containers restart automatically
✅ **Isolated** - Doesn't affect your system Python
✅ **Easy backup** - Just copy the `data/` folder
✅ **OrbStack optimized** - Fast, lightweight, native Mac performance

## Quick Start

### 1. Prerequisites

Make sure you have OrbStack installed and running:
```bash
# Check if OrbStack is running
docker ps
```

### 2. Create Environment File

```bash
# Create .env file with your SEC identity
echo 'SEC_IDENTITY="CompanyDataHub skyleryh6km@gmail.com"' > .env
```

### 3. Initial Setup & Run

```bash
# Build and start all services
docker-compose up -d

# Watch the logs
docker-compose logs -f
```

That's it! The system is now:
- 📊 Dashboard running at **http://localhost:8000**
- 📰 Collecting news every 24 hours
- 📄 Collecting SEC filings every 24 hours
- 💾 Storing data in `./data/finance.db`

## What Gets Created

Docker Compose creates 3 containers:

1. **dashboard** - Web UI (port 8000)
2. **scraper-news** - Collects news daily
3. **scraper-filings** - Collects SEC filings daily

## Management Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f dashboard
docker-compose logs -f scraper-news
docker-compose logs -f scraper-filings

# Restart a service
docker-compose restart dashboard

# Run one-time scraping (override the schedule)
docker-compose run --rm scraper-news python scrape.py
docker-compose run --rm scraper-filings python scrape_filings.py

# Check database stats
docker-compose run --rm dashboard python store.py --stats

# Access database directly
docker-compose run --rm dashboard sqlite3 /data/finance.db
```

## Initial Backfill

To collect all historical data since 2024:

```bash
# Run initial SEC filing backfill (takes ~10 minutes)
docker-compose run --rm scraper-filings python scrape_filings.py --since 2024-01-01

# Run initial news collection
docker-compose run --rm scraper-news python scrape.py
```

## Accessing Your Data

### Via Web Dashboard
Open **http://localhost:8000** in your browser

### Via Database File
The SQLite database is at `./data/finance.db`

You can access it directly:
```bash
sqlite3 ./data/finance.db
```

Or copy it out:
```bash
cp ./data/finance.db ~/Desktop/finance.db
```

## Customization

### Change Collection Schedule

Edit `docker-compose.yml` and modify the `sleep` duration:

```yaml
# Run every 6 hours instead of 24
sleep 21600  # 6 hours in seconds

# Run every hour
sleep 3600   # 1 hour in seconds
```

Then restart:
```bash
docker-compose restart scraper-news scraper-filings
```

### Change Dashboard Port

Edit `docker-compose.yml`:
```yaml
ports:
  - "8080:8000"  # Access at http://localhost:8080
```

## Backup Your Data

Everything is in the `data/` folder:

```bash
# Backup
tar -czf company-data-backup-$(date +%Y%m%d).tar.gz data/

# Restore
tar -xzf company-data-backup-20260623.tar.gz
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Database locked error
```bash
# Stop all containers
docker-compose down

# Wait 5 seconds, then restart
sleep 5
docker-compose up -d
```

### Out of space
```bash
# Clean up old Docker images
docker system prune -a

# Check database size
du -sh data/finance.db
```

### Can't connect to dashboard
```bash
# Check if container is running
docker-compose ps

# Check logs
docker-compose logs dashboard

# Restart dashboard
docker-compose restart dashboard
```

## OrbStack-Specific Features

### View in OrbStack UI
1. Open OrbStack app
2. Go to "Containers" tab
3. See your 3 running containers
4. Click any container to view logs

### Resource Usage
OrbStack shows real-time CPU/memory usage per container

### Quick Access
Right-click container in OrbStack → "Open in Browser" (for dashboard)

## Advanced: Using OrbStack CLI

```bash
# List running containers
orb list

# Open shell in container
orb exec company-data-hub-dashboard-1 /bin/bash

# View container stats
orb stats

# Quick restart
orb restart company-data-hub-dashboard-1
```

## Comparison: Docker vs. Native

| Feature | Docker | Native Python |
|---------|--------|---------------|
| Setup | 1 command | Multiple steps |
| Dependencies | Isolated | System-wide |
| Auto-restart | Yes | Needs launchd |
| Portability | Any system | macOS only |
| Performance | ~95% native | 100% |
| OrbStack integration | Excellent | N/A |

**Recommendation:** Use Docker if you want:
- Simplest setup
- Always-on service
- Easy backup/restore
- To run on multiple machines

## Production Tips

### 1. Persistent Data
Data is stored in `./data/` - this folder survives container restarts

### 2. Environment Variables
Never commit `.env` to git - it's already in `.gitignore`

### 3. Logs
Logs are stored in container memory by default. For persistent logs:

```yaml
# Add to docker-compose.yml under each service
volumes:
  - ./logs:/app/logs
```

### 4. Monitoring
Set up health checks:

```yaml
# Add to dashboard service in docker-compose.yml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000"]
  interval: 30s
  timeout: 10s
  retries: 3
```

## Updating

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

## Complete Teardown

To completely remove everything:

```bash
# Stop and remove containers
docker-compose down

# Remove data (WARNING: deletes all collected data!)
rm -rf data/

# Remove Docker images
docker rmi company-data-hub_dashboard
docker rmi company-data-hub_scraper-news
docker rmi company-data-hub_scraper-filings
```

---

## Next Steps

After Docker is running:

1. **Verify collection**: `docker-compose logs -f`
2. **Open dashboard**: http://localhost:8000
3. **Check stats**: `docker-compose run --rm dashboard python store.py --stats`
4. **Let it run** - Data collects automatically every 24 hours
