module.exports = {
  apps: [
    {
      name: 'coal-miner',
      script: 'bot_optimized.py',
      interpreter: 'python3',
      cwd: '/root/mining-bot',  // Ganti dengan path VPS kamu
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        PYTHONUNBUFFERED: '1'
      },
      error_file: 'logs/error.log',
      out_file: 'logs/output.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 5000
    }
  ]
};
