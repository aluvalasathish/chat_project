import os
import sys
import django
from pathlib import Path

# Add the project directory to the Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_project.settings_prod')
django.setup()

# Import after Django setup
from channels.routing import get_default_application
application = get_default_application() 