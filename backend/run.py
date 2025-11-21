#!/usr/bin/env python3
"""
Run script for the AI Security Analytics Backend
"""

import os
import sys

# Add the backend directory to Python path
sys.path.append(os.path.dirname(__file__))

from app import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"Starting AI Security Analytics Backend on port {port}")
    print(f"Debug mode: {debug}")
    print(f"Access the application at: http://localhost:{port}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )