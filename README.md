# camera-person-counter
This project implements a camera person counter system using YOLO for detection and counting on a Raspberry Pi 4B.

## Project Structure
```
camera-person-counter
├── src
│   ├── main.py          # Entry point of the application
│   ├── detector
│   │   ├── __init__.py  # Package initialization
│   │   └── yolo.py      # YOLO detection logic
│   ├── counter
│   │   ├── __init__.py  # Package initialization
│   │   └── counter.py    # Person counting logic
│   ├── camera
│   │   ├── __init__.py  # Package initialization
│   │   └── picamera.py   # Raspberry Pi camera interface
│   ├── utils
│   │   ├── __init__.py  # Package initialization
│   │   └── visualization.py # Visualization utilities
│   └── config.py        # Configuration settings
├── requirements.txt      # Project dependencies
├── models
│   └── .gitkeep          # Keep models directory in version control
└── README.md             # Project documentation
```

## Setup Instructions
1. Clone the repository:
   ```
   git clone <repository-url>
   cd camera-person-counter
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure the model paths and detection thresholds in `src/config.py`.

4. Run the application:
   ```
   python src/main.py
   ```

## Usage Guidelines
- Ensure the Raspberry Pi camera is properly connected and enabled.
- Adjust the detection thresholds in `config.py` as needed for optimal performance.
- Monitor the output for detected persons and the counting results.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.





uict@raspberrypi:~/Desktop/camera-person-counter-UICT $ python3 src/web_app.py
Attempting to connect to camera 0
(24712) wsgi starting up on http://0.0.0.0:5000
(24712) accepted ('127.0.0.1', 35162)
127.0.0.1 - - [21/Apr/2025 07:05:33] "GET /socket.io/?EIO=4&transport=polling&t=PPP6G7q HTTP/1.1" 200 300 0.002078
127.0.0.1 - - [21/Apr/2025 07:05:33] "POST /socket.io/?EIO=4&transport=polling&t=PPP6G8F&sid=2XVIfY3X2q97OKxAAAAA HTTP/1.1" 200 217 0.007315
(24712) accepted ('127.0.0.1', 35174)
(24712) accepted ('127.0.0.1', 35180)
127.0.0.1 - - [21/Apr/2025 07:05:33] "GET /socket.io/?EIO=4&transport=polling&t=PPP6G8S&sid=2XVIfY3X2q97OKxAAAAA HTTP/1.1" 200 213 0.001234
127.0.0.1 - - [21/Apr/2025 07:05:33] "GET /socket.io/?EIO=4&transport=polling&t=PPP6G99&sid=2XVIfY3X2q97OKxAAAAA HTTP/1.1" 200 181 0.000947
127.0.0.1 - - [21/Apr/2025 07:05:34] "GET /socket.io/?EIO=4&transport=polling&t=PPP6GQL HTTP/1.1" 200 300 0.001008
127.0.0.1 - - [21/Apr/2025 07:05:34] "POST /socket.io/?EIO=4&transport=polling&t=PPP6GQX&sid=yoM_XM5u58BPvfcoAAAC HTTP/1.1" 200 217 0.002033
(24712) accepted ('127.0.0.1', 35188)
127.0.0.1 - - [21/Apr/2025 07:05:34] "GET /socket.io/?EIO=4&transport=polling&t=PPP6GQe&sid=yoM_XM5u58BPvfcoAAAC HTTP/1.1" 200 213 0.000926
127.0.0.1 - - [21/Apr/2025 07:05:34] "GET /socket.io/?EIO=4&transport=polling&t=PPP6GRC&sid=yoM_XM5u58BPvfcoAAAC HTTP/1.1" 200 181 0.000952
127.0.0.1 - - [21/Apr/2025 07:05:42] "GET /socket.io/?EIO=4&transport=websocket&sid=2XVIfY3X2q97OKxAAAAA HTTP/1.1" 200 0 9.498796
127.0.0.1 - - [21/Apr/2025 07:05:42] "GET / HTTP/1.1" 200 3352 0.020509
Video feed requested. Camera status: OK
[WARNING] Warning: Low frame rate detected (0.1 FPS)
Error in frame generation: object of type 'function' has no len()
127.0.0.1 - - [21/Apr/2025 07:05:43] "GET / HTTP/1.1" 200 3352 0.011980
Video feed requested. Camera status: OK
(24712) accepted ('127.0.0.1', 47024)
127.0.0.1 - - [21/Apr/2025 07:05:43] "GET / HTTP/1.1" 200 3352 0.004601
Video feed requested. Camera status: OK
Traceback (most recent call last):
  File "/home/uict/.local/lib/python3.9/site-packages/eventlet/wsgi.py", line 641, in handle_one_response
    write(b''.join(towrite))
  File "/home/uict/.local/lib/python3.9/site-packages/eventlet/wsgi.py", line 574, in write
    wfile.writelines(towrite)
  File "/usr/lib/python3.9/socket.py", line 722, in write
    return self._sock.send(b)
  File "/home/uict/.local/lib/python3.9/site-packages/eventlet/greenio/base.py", line 383, in send
    return self._send_loop(self.fd.send, data, flags)
  File "/home/uict/.local/lib/python3.9/site-packages/eventlet/greenio/base.py", line 370, in _send_loop
    return send_method(data, *args)
BrokenPipeError: [Errno 32] Broken pipe

127.0.0.1 - - [21/Apr/2025 07:05:43] "GET /video_feed HTTP/1.1" 200 53134 0.139535
(24712) accepted ('127.0.0.1', 47034)
127.0.0.1 - - [21/Apr/2025 07:05:43] "GET / HTTP/1.1" 200 3352 0.004065
Traceback (most recent call last):
  File "/home/uict/.local/lib/python3.9/site-packages/eventlet/wsgi.py", line 641, in handle_one_response
    write(b''.join(towrite))
  File "/home/uict/.local/lib/python3.9/site-packages/eventlet/wsgi.py", line 574, in write
    wfile.writelines(towrite)
  File "/usr/lib/python3.9/socket.py", line 722, in write
    return self._sock.send(b)
  File "/home/uict/.local/lib/python3.9/site-packages/eventlet/greenio/base.py", line 383, in send
    return self._send_loop(self.fd.send, data, flags)
  File "/home/uict/.local/lib/python3.9/site-packages/eventlet/greenio/base.py", line 370, in _send_loop
    return send_method(data, *args)
BrokenPipeError: [Errno 32] Broken pipe

127.0.0.1 - - [21/Apr/2025 07:05:43] "GET /video_feed HTTP/1.1" 200 43731 0.618695
Video feed requested. Camera status: OK
Traceback (most recent call last):
  File "/home/uict/.local/lib/python3.9/site-packages/eventlet/wsgi.py", line 641, in handle_one_response
    write(b''.join(towrite))
  File "/home/uict/.local/lib/python3.9/site-packages/eventlet/wsgi.py", line 574, in write
    wfile.writelines(towrite)
  File "/usr/lib/python3.9/socket.py", line 722, in write
    return self._sock.send(b)
  File "/home/uict/.local/lib/python3.9/site-packages/eventlet/greenio/base.py", line 383, in send
    return self._send_loop(self.fd.send, data, flags)
  File "/home/uict/.local/lib/python3.9/site-packages/eventlet/greenio/base.py", line 370, in _send_loop
    return send_method(data, *args)
BrokenPipeError: [Errno 32] Broken pipe

127.0.0.1 - - [21/Apr/2025 07:05:43] "GET /video_feed HTTP/1.1" 200 140569 0.363644
[WARNING] Warning: Low frame rate detected (16.8 FPS)
Error in frame generation: object of type 'function' has no len()
(24712) accepted ('127.0.0.1', 47038)
127.0.0.1 - - [21/Apr/2025 07:05:44] "GET /socket.io/?EIO=4&transport=polling&t=PPP6Inp HTTP/1.1" 200 300 0.001807
127.0.0.1 - - [21/Apr/2025 07:05:44] "POST /socket.io/?EIO=4&transport=polling&t=PPP6IoU&sid=HGcnrV48BRZ4QA78AAAE HTTP/1.1" 200 217 0.002186
(24712) accepted ('127.0.0.1', 47050)
127.0.0.1 - - [21/Apr/2025 07:05:44] "GET /socket.io/?EIO=4&transport=polling&t=PPP6Ioh&sid=HGcnrV48BRZ4QA78AAAE HTTP/1.1" 200 181 0.000843
127.0.0.1 - - [21/Apr/2025 07:05:44] "GET /socket.io/?EIO=4&transport=polling&t=PPP6Ip6&sid=HGcnrV48BRZ4QA78AAAE HTTP/1.1" 200 181 0.001334
(24712) accepted ('127.0.0.1', 47060)
127.0.0.1 - - [21/Apr/2025 07:05:44] "GET /favicon.ico HTTP/1.1" 404 355 0.005300
[WARNING] Warning: Low frame rate detected (10.7 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (10.9 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (10.7 FPS)
Error in frame generation: object of type 'function' has no len()
127.0.0.1 - - [21/Apr/2025 07:05:47] "GET /socket.io/?EIO=4&transport=websocket&sid=yoM_XM5u58BPvfcoAAAC HTTP/1.1" 200 0 12.924640
[WARNING] Warning: Low frame rate detected (10.4 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (10.7 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (10.8 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (10.7 FPS)
Error in frame generation: object of type 'function' has no len()
[INFO] Tracking started
[ERROR] Error during detection: detect() takes 2 positional arguments but 3 were given
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (1.9 FPS)
Error in frame generation: object of type 'function' has no len()
[ERROR] Error during detection: detect() takes 2 positional arguments but 3 were given
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (1.9 FPS)
Error in frame generation: object of type 'function' has no len()
[ERROR] Error during detection: detect() takes 2 positional arguments but 3 were given
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (1.9 FPS)
Error in frame generation: object of type 'function' has no len()
[ERROR] Error during detection: detect() takes 2 positional arguments but 3 were given
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (1.9 FPS)
Error in frame generation: object of type 'function' has no len()
[ERROR] Error during detection: detect() takes 2 positional arguments but 3 were given
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (1.9 FPS)
Error in frame generation: object of type 'function' has no len()
[ERROR] Error during detection: detect() takes 2 positional arguments but 3 were given
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (1.9 FPS)
Error in frame generation: object of type 'function' has no len()
[ERROR] Error during detection: detect() takes 2 positional arguments but 3 were given
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (1.9 FPS)
Error in frame generation: object of type 'function' has no len()
[INFO] Tracking stopped
[WARNING] Warning: Low frame rate detected (11.0 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (11.5 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (11.0 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (10.9 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (10.8 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (10.5 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (10.0 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (9.9 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (9.8 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (10.0 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (10.7 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (10.6 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (10.9 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (10.7 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (10.7 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (11.6 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (11.5 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (11.6 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (11.7 FPS)
Error in frame generation: object of type 'function' has no len()
^Cwsgi exiting
127.0.0.1 - - [21/Apr/2025 07:06:18] "GET /socket.io/?EIO=4&transport=websocket&sid=HGcnrV48BRZ4QA78AAAE HTTP/1.1" 200 0 33.762388
[WARNING] Warning: Low frame rate detected (11.7 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (10.7 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (11.6 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (11.7 FPS)
Error in frame generation: object of type 'function' has no len()
[WARNING] Warning: Low frame rate detected (11.7 FPS)
Error in frame generation: object of type 'function' has no len()