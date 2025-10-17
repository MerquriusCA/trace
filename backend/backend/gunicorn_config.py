"""
Gunicorn configuration file for Railway deployment
"""
import os

# Get port from environment
port = os.environ.get('PORT', '8000')

# Server socket
bind = f"0.0.0.0:{port}"

# Worker processes
workers = 1
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 2

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Process naming
proc_name = 'trace-backend'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL
keyfile = None
certfile = None

print(f"📍 Gunicorn starting on port {port}")
print(f"🔗 Bind address: {bind}")
print(f"⚙️ Workers: {workers}")