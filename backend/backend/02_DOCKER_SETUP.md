# 🐳 Full Docker Development Setup

This setup runs everything in Docker containers: PostgreSQL database, Flask app, and pgAdmin. This provides perfect production parity and eliminates all dependency issues.

## 🚀 Quick Start

```bash
# Start everything with one command
docker-compose up --build
```

Or to run in background:
```bash
docker-compose up -d --build
```

## 📋 Prerequisites

- Docker Desktop installed and running
- That's it! No Python dependencies needed on your machine

## 🔧 Container Architecture

The setup includes 3 containers:
- **`chrome_ext_app`** - Flask application with hot-reload
- **`chrome_ext_postgres`** - PostgreSQL 15 database  
- **`chrome_ext_pgadmin`** - Web-based database management

## 🛠️ Development Commands

```bash
# Start all services (rebuild if needed)
docker-compose up --build

# Start in background
docker-compose up -d --build

# View logs
docker-compose logs -f app
docker-compose logs -f postgres

# Stop all services
docker-compose down

# Reset everything (removes data)
docker-compose down -v

# Rebuild just the app
docker-compose build app
```

## 📊 Service Access

| Service | URL | Credentials |
|---------|-----|-------------|
| **Flask App** | http://localhost:8000 | - |
| **PostgreSQL** | localhost:5433 | user: `chrome_user`<br>pass: `chrome_password`<br>db: `chrome_extension` |
| **pgAdmin** | http://localhost:5050 | email: `admin@example.com`<br>pass: `admin` |

## 🗄️ Database Management

### Connect to PostgreSQL

```bash
# Via Docker container (recommended)
docker-compose exec postgres psql -U chrome_user -d chrome_extension

# Via app container (for debugging)
docker-compose exec app python -c "from app import db; print('Database connected!')"

# Via local client (if PostgreSQL installed locally)
psql -h localhost -p 5433 -U chrome_user -d chrome_extension
```

### Common SQL Commands

```sql
-- List tables
\dt

-- View users table
SELECT * FROM users;

-- Check subscriptions
SELECT email, subscription_status, created_at FROM users;

-- Exit psql
\q
```

### pgAdmin Setup

1. Go to http://localhost:5050
2. Login with `admin@example.com` / `admin`
3. Add new server:
   - **Name**: Chrome Extension DB
   - **Host**: `postgres` (container name - important!)
   - **Port**: `5432` (internal container port)
   - **Database**: `chrome_extension`
   - **Username**: `chrome_user`
   - **Password**: `chrome_password`

## 🛠️ Development Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f postgres
docker-compose logs -f pgadmin

# Stop services
docker-compose down

# Reset database (removes all data)
docker-compose down -v
docker-compose up -d

# Access PostgreSQL shell
docker-compose exec postgres psql -U chrome_user -d chrome_extension
```


## 🔄 Hot Reload Development

The Flask app supports hot reload! When you edit Python files:
1. The container detects changes via volume mount
2. Flask automatically restarts the server
3. Your changes are immediately available

```bash
# Watch logs to see restarts
docker-compose logs -f app
```

## 🐛 Troubleshooting

### Container Issues

```bash
# Check all containers
docker-compose ps

# View logs for specific service
docker-compose logs app
docker-compose logs postgres
docker-compose logs pgadmin

# Restart specific service
docker-compose restart app
```

### Database Connection Issues

```bash
# Test database from app container
docker-compose exec app python -c "
from app import db
from sqlalchemy import text
try:
    db.session.execute(text('SELECT 1'))
    print('✅ Database connection works!')
except Exception as e:
    print(f'❌ Database error: {e}')
"
```

### Port Conflicts

If ports are in use, edit `docker-compose.yml`:
- App: Change `"8000:8000"` to `"8001:8000"`
- PostgreSQL: Change `"5433:5432"` to `"5434:5432"`
- pgAdmin: Change `"5050:80"` to `"5051:80"`

### Complete Reset

```bash
# Nuclear option - removes all data and containers
docker-compose down -v
docker system prune -f
docker-compose up --build
```

## 🔧 Environment Files

- **`.env`** - Main environment (uses PostgreSQL)
- **`.env.docker`** - Docker-specific settings

## 📦 Docker Services

The `docker-compose.yml` includes:

- **PostgreSQL 15** - Production-grade database
- **pgAdmin 4** - Web-based database management
- **Persistent volumes** - Data survives container restarts
- **Health checks** - Ensures services are ready
- **Custom network** - Isolated networking

## 🚀 Production Parity

This setup matches Railway's PostgreSQL exactly:
- Same PostgreSQL version (15)
- Same connection patterns
- Same environment variables
- Same database schema