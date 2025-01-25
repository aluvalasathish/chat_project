# Django Real-Time Chat Application

Real-time chat application built with Django, Channels, and WebSocket support. Features user authentication, activity tracking, and message history.

## Key Features

- Real-time WebSocket messaging
- User authentication & activity tracking
- Message history & REST API
- Production-ready configuration
- Redis channel layer for broadcasting

## Tech Stack

- Django 4.x with Channels
- Django REST Framework
- PostgreSQL / SQLite
- Redis & Daphne ASGI Server
- Nginx & CORS Headers

## Quick Start

### Prerequisites

- Python 3.8+
- Redis Server
- Git
- pip and virtualenv

### Local Development

```bash
# Clone repository
git clone https://github.com/aluvalasathish/chat_project.git
cd chat_project

# Setup virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
# Create .env file with:
SECRET_KEY=your_secret_key
DEBUG=True
DB_NAME=chat_db
DB_USER=chat_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
REDIS_HOST=localhost

# Initialize database
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

# Start Redis
redis-server  # Windows (WSL)
# brew services start redis  # MacOS
# sudo service redis-server start  # Linux

# Run servers
python manage.py runserver  # Django server
python daphne_server.py    # WebSocket server
```

Access at:
- App: http://localhost:8000
- WebSocket: ws://localhost:8001
- Admin: http://localhost:8000/admin

## Production Deployment

### 1. System Setup

```bash
# Update system and install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv nginx postgresql postgresql-contrib redis-server supervisor

# Configure PostgreSQL
sudo -u postgres psql
postgres=# CREATE DATABASE chat_db;
postgres=# CREATE USER chat_user WITH PASSWORD 'your_password';
postgres=# ALTER ROLE chat_user SET client_encoding TO 'utf8';
postgres=# ALTER ROLE chat_user SET default_transaction_isolation TO 'read committed';
postgres=# ALTER ROLE chat_user SET timezone TO 'UTC';
postgres=# GRANT ALL PRIVILEGES ON DATABASE chat_db TO chat_user;
postgres=# \q
```

### 2. Project Setup

```bash
# Create project directory
sudo mkdir -p /var/www/chat
sudo chown -R $USER:$USER /var/www/chat

# Clone and setup project
git clone https://github.com/aluvalasathish/chat_project.git /var/www/chat
cd /var/www/chat
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.prod.txt
pip install gunicorn

# Create .env file
cat > .env << EOL
DEBUG=False
SECRET_KEY=your_secure_secret_key
ALLOWED_HOSTS=your_domain.com,www.your_domain.com
DB_NAME=chat_db
DB_USER=chat_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
REDIS_HOST=localhost
REDIS_PORT=6379
EOL

# Setup static files
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py createsuperuser
```

### 3. Gunicorn Setup

Create `/etc/supervisor/conf.d/chat_gunicorn.conf`:
```ini
[program:chat_gunicorn]
directory=/var/www/chat
command=/var/www/chat/venv/bin/gunicorn --workers 3 --bind unix:/var/www/chat/chat.sock chat_project.wsgi:application
autostart=true
autorestart=true
stderr_logfile=/var/log/chat_gunicorn.err.log
stdout_logfile=/var/log/chat_gunicorn.out.log
user=www-data
group=www-data
environment=DJANGO_SETTINGS_MODULE="chat_project.settings_prod"
```

### 4. Daphne Setup

Create `/etc/supervisor/conf.d/chat_daphne.conf`:
```ini
[program:chat_daphne]
directory=/var/www/chat
command=/var/www/chat/venv/bin/daphne -b 0.0.0.0 -p 8001 chat_project.asgi:application
autostart=true
autorestart=true
stderr_logfile=/var/log/chat_daphne.err.log
stdout_logfile=/var/log/chat_daphne.out.log
user=www-data
group=www-data
environment=DJANGO_SETTINGS_MODULE="chat_project.settings_prod"
```

### 5. Nginx Configuration

Create `/etc/nginx/sites-available/chat`:
```nginx
upstream channels-backend {
    server localhost:8001;
}

server {
    listen 80;
    server_name your_domain.com www.your_domain.com;

    location = /favicon.ico { 
        access_log off; 
        log_not_found off; 
    }

    location /static/ {
        root /var/www/chat;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location /media/ {
        root /var/www/chat;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location /ws/ {
        proxy_pass http://channels-backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_read_timeout 86400;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/chat/chat.sock;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
        proxy_redirect off;
        client_max_body_size 100M;
    }
}
```

### 6. Final Configuration

```bash
# Setup permissions
sudo chown -R www-data:www-data /var/www/chat
sudo chmod -R 755 /var/www/chat

# Enable and start services
sudo ln -s /etc/nginx/sites-available/chat /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart all

# Check status
sudo supervisorctl status
```

```

## Maintenance

### Logs
```bash
# Application logs
sudo tail -f /var/log/chat_gunicorn.out.log
sudo tail -f /var/log/chat_daphne.out.log

# Error logs
sudo tail -f /var/log/chat_gunicorn.err.log
sudo tail -f /var/log/chat_daphne.err.log

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Updates
```bash
cd /var/www/chat
source venv/bin/activate
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo supervisorctl restart all
sudo systemctl restart nginx
```

## Troubleshooting

1. WebSocket Issues
   - Check Daphne status: `sudo supervisorctl status chat_daphne`
   - Verify port 8001 is open: `sudo netstat -tulpn | grep 8001`
   - Check Daphne logs

2. Static Files
   - Verify file permissions
   - Check Nginx configuration
   - Run collectstatic again

3. Database Connection
   - Check PostgreSQL status: `sudo systemctl status postgresql`
   - Verify database credentials
   - Ensure migrations are applied

## Security Best Practices

- Keep DEBUG=False in production
- Use strong SECRET_KEY
- Enable SSL/TLS (HTTPS)
- Configure ALLOWED_HOSTS properly
- Secure Redis connection (password, bind address)
- Regular security updates
- Implement rate limiting
- Use secure headers
- Monitor logs for suspicious activity

## License

MIT License
