#!/bin/bash

echo "Installing requirements..."
pip install -r requirements.txt

echo "Making migrations..."
python manage.py makemigrations
python manage.py migrate

echo "Starting Django development server..."
python manage.py runserver &

echo "Waiting for Django server to start..."
sleep 5

echo "Starting Daphne server..."
python -m daphne -b 127.0.0.1 -p 8001 chat_project.asgi:application 