import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import app

# Vercel looks for a variable named 'app'
# Your app.py already exports 'app' — done!