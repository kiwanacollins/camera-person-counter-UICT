# filepath: /Users/kiwana/Desktop/camera-person-counter/src/main.py
import sys
import os

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app from web_app.py
from web_app import app, socketio

def main():
    # Run the Flask web server with Socket.IO
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)

if __name__ == "__main__":
    main()
    