#!/bin/bash

# Exit on error
set -e

echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

echo "Installing system dependencies..."
sudo apt-get install -y python3-pip python3-dev libpq-dev postgresql postgresql-contrib nginx redis-server supervisor nodejs npm

# Install Tailwind CSS and required packages
echo "Installing Tailwind CSS..."
npm init -y  # Initialize npm if not already done
npm install -D tailwindcss postcss autoprefixer

# Create Tailwind configuration files
npx tailwindcss init  # Create tailwind.config.js

echo "Setting up PostCSS configuration..."
cat > postcss.config.js <<EOL
module.exports = {
  plugins: [
    require('tailwindcss'),
    require('autoprefixer'),
  ],
}
EOL

# Create your CSS file and add Tailwind's base, components, and utilities
echo "Setting up Tailwind CSS file..."
mkdir -p static/css
cat > static/css/styles.css <<EOL
@tailwind base;
@tailwind components;
@tailwind utilities;
EOL

# Create a script in package.json to build the CSS
echo "Creating build script..."
cat > package.json <<EOL
{
  "scripts": {
    "build": "tailwindcss build static/css/styles.css -o static/css/output.css"
  }
}
EOL

# Run Tailwind build to generate the production CSS
echo "Building Tailwind CSS for production..."
npm run build

# Create necessary directories
echo "Creating project directories..."
mkdir -p /home/ubuntu/chat_project/logs
mkdir -p /home/ubuntu/chat_project/media
mkdir -p /home/ubuntu/chat_project/static
mkdir -p /home/ubuntu/backups

echo "Setting up PostgreSQL..."

# Create the database if it does not already exist
sudo -u postgres psql -c "SELECT 1 FROM pg_catalog.pg_database WHERE datname = 'chat_db' LIMIT 1" | grep -q 1 || sudo -u postgres psql -c "CREATE DATABASE chat_db;"

# Create the user if it does not already exist
sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname = 'chat_user'" | grep -q 1 || sudo -u postgres psql -c "CREATE USER chat_user WITH PASSWORD 'aluvala';"

# Set configurations for the user
sudo -u postgres psql -c "ALTER ROLE chat_user SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE chat_user SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE chat_user SET timezone TO 'UTC';"

# Grant privileges to the user if not already granted
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE chat_db TO chat_user;"

# Get EC2 instance public IP
EC2_PUBLIC_IP=$(curl -s http://ec2-13-60-170-174.eu-north-1.compute.amazonaws.com)

echo "Creating .env file..."
cat > .env << EOL
DJANGO_SETTINGS_MODULE=chat_project.settings_prod
DB_NAME=chat_db
DB_USER=chat_user
DB_PASSWORD=aluvala
DB_HOST=localhost
DB_PORT=5432
DOMAIN_NAME=$EC2_PUBLIC_IP
REDIS_HOST=localhost
ALLOWED_HOSTS=$EC2_PUBLIC_IP,localhost,127.0.0.1
EOL

echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Installing Python dependencies..."
pip install -r requirements.prod.txt

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Running migrations..."
python manage.py migrate

echo "Setting up Gunicorn..."
sudo cp gunicorn.service /etc/systemd/system/
sudo systemctl start gunicorn
sudo systemctl enable gunicorn

echo "Setting up Supervisor for Daphne..."
sudo cp daphne.conf /etc/supervisor/conf.d/
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start daphne

echo "Setting up Nginx..."
# Backup default nginx config
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup

# Update nginx config with AWS specific settings
sudo cp nginx.conf /etc/nginx/sites-available/chat_project
sudo ln -sf /etc/nginx/sites-available/chat_project /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo "Starting Redis..."
sudo systemctl start redis-server
sudo systemctl enable redis-server

echo "Setting up daily database backup..."
(crontab -l 2>/dev/null; echo "0 0 * * * pg_dump chat_db > /home/ubuntu/backups/chat_db_\$(date +\%Y\%m\%d).sql") | crontab -

echo "Setting up firewall..."
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 8001
sudo ufw --force enable

echo "Deployment complete!"
echo "Your application should be accessible at: http://$EC2_PUBLIC_IP"
echo "Please set up your domain and SSL certificate using Certbot with:"
echo "sudo certbot --nginx -d your_domain.com"
