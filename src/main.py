# filepath: /Users/kiwana/Desktop/camera-person-counter/src/main.py
import sys
import os

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app from web_app.py (with proper import path)
from src.web_app import app, socketio

def main():
    print("Starting Person Counter web server...")
    print("Access the application at http://localhost:5000")
    # Run the Flask web server with Socket.IO
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)

if __name__ == "__main__":
    main()
