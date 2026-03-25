# PM2 Commands untuk COAL Mining Bot

## Setup Awal

```bash
# 1. Upload folder mining-bot ke VPS
scp -r mining-bot user@your-vps-ip:/root/

# 2. SSH ke VPS
ssh user@your-vps-ip

# 3. Masuk ke folder
cd /root/mining-bot

# 4. Jalankan setup script
chmod +x setup_vps.sh
./setup_vps.sh

# 5. Edit config
nano config.json
# Isi wallet dan API key

# 6. Edit ecosystem.config.js
nano ecosystem.config.js
# Ganti path 'cwd' sesuai lokasi folder kamu
```

## Start Mining

```bash
# Start bot dengan PM2
pm2 start ecosystem.config.js

# Save PM2 config (auto-start on reboot)
pm2 save

# Setup auto-start on boot
pm2 startup
# Copy-paste command yang muncul, lalu run
```

## Monitor Bot

```bash
# Lihat status
pm2 status

# Lihat logs real-time
pm2 logs coal-miner

# Lihat logs (last 100 lines)
pm2 logs coal-miner --lines 100

# Monitor CPU/Memory
pm2 monit

# Dashboard web (optional)
pm2 plus
```

## Control Bot

```bash
# Stop bot
pm2 stop coal-miner

# Restart bot
pm2 restart coal-miner

# Reload bot (zero-downtime)
pm2 reload coal-miner

# Delete bot dari PM2
pm2 delete coal-miner
```

## Logs

```bash
# Lihat error logs
pm2 logs coal-miner --err

# Lihat output logs
pm2 logs coal-miner --out

# Clear logs
pm2 flush coal-miner

# Lokasi log files
# Output: logs/output.log
# Error: logs/error.log
```

## Troubleshooting

```bash
# Bot tidak start
pm2 logs coal-miner --lines 50

# Check Python version
python3 --version

# Check dependencies
pip3 list | grep requests

# Restart PM2
pm2 kill
pm2 start ecosystem.config.js

# Check disk space
df -h

# Check memory
free -h
```

## Update Bot

```bash
# Stop bot
pm2 stop coal-miner

# Update files (upload new bot_optimized.py)
# Or edit directly:
nano bot_optimized.py

# Restart
pm2 restart coal-miner

# Check logs
pm2 logs coal-miner
```

## Multiple Wallets (Advanced)

Edit `ecosystem.config.js`:

```javascript
module.exports = {
  apps: [
    {
      name: 'coal-miner-1',
      script: 'bot_optimized.py',
      interpreter: 'python3',
      cwd: '/root/mining-bot-1',
      // ... config
    },
    {
      name: 'coal-miner-2',
      script: 'bot_optimized.py',
      interpreter: 'python3',
      cwd: '/root/mining-bot-2',
      // ... config
    }
  ]
};
```

Then:
```bash
pm2 start ecosystem.config.js
pm2 save
```

## Auto-restart on Crash

PM2 sudah auto-restart by default. Config di ecosystem.config.js:
- `autorestart: true` - Auto restart on crash
- `max_restarts: 10` - Max restart attempts
- `min_uptime: '10s'` - Minimum uptime before considered stable
- `restart_delay: 5000` - Wait 5s before restart

## Backup Stats

```bash
# Stats disimpan di mining_stats.json
# Backup secara berkala:
cp mining_stats.json mining_stats.backup.json

# Atau setup cron untuk auto-backup
crontab -e
# Add line:
0 */6 * * * cp /root/mining-bot/mining_stats.json /root/mining-bot/backups/stats_$(date +\%Y\%m\%d_\%H\%M).json
```

## Check Mining Performance

```bash
# Lihat stats file
cat mining_stats.json | python3 -m json.tool

# Atau buat script checker
python3 check_rank.py
```

## Security Tips

1. **Jangan expose API key** - Pastikan config.json tidak di-commit ke git
2. **Firewall** - Setup UFW untuk block unused ports
3. **SSH Key** - Gunakan SSH key instead of password
4. **Update regularly** - Keep system updated

```bash
# Setup firewall
sudo ufw allow 22/tcp
sudo ufw enable
```
