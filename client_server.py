import socket
import sys
import threading
import time
from pynput import mouse
import platform

class MouseClient:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.mouse_listener = None
        self.coordinate_count = 0
        self.last_coordinates = None
        self.last_print_time = time.time()
        
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"Connected to server at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            return False
    
    def send_coordinates(self, coordinates):
        try:
            message = coordinates + '\n'
            self.socket.send(message.encode('utf-8'))
            return True
        except Exception as e:
            print(f"Failed to send coordinates: {e}")
            return False
    
    def disconnect(self):
        self.running = False
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.socket:
            self.socket.close()
            print("Disconnected from server")
    
    def on_move(self, x, y):
        print(f"DEBUG: on_move called with x={x}, y={y}, running={self.running}")  # Debug line
        if self.running:
            coordinates = f"{int(x)},{int(y)}"
            print(f"DEBUG: Coordinates formatted: {coordinates}")  # Debug line
            
            # Always print the first coordinate to confirm it's working
            if self.coordinate_count == 0:
                print(f"✅ Mouse tracking is working! First coordinate: {coordinates}")
            
            if self.send_coordinates(coordinates):
                self.coordinate_count += 1
                self.last_coordinates = coordinates
                
                # Print every 10th coordinate or every 0.5 seconds
                current_time = time.time()
                if self.coordinate_count % 10 == 0 or (current_time - self.last_print_time) >= 0.5:
                    print(f"[CLIENT] Sent: {coordinates} (Total: {self.coordinate_count} coordinates)")
                    self.last_print_time = current_time
            else:
                print(f"DEBUG: Failed to send coordinates")  # Debug line
    
    def on_click(self, x, y, button, pressed):
        if pressed and button == mouse.Button.right:
            print("Right click detected - stopping mouse tracking")
            self.running = False
            return False
    
    def start_mouse_listener(self):
        try:
            self.mouse_listener = mouse.Listener(
                on_move=self.on_move,
                on_click=self.on_click
            )
            self.mouse_listener.start()
            print("Mouse listener started successfully")
        except Exception as e:
            print(f"ERROR: Failed to start mouse listener: {e}")
            if platform.system() == 'Darwin':  # macOS
                print("\n⚠️  PERMISSION ERROR DETECTED ⚠️")
                print("On macOS, you need to grant Accessibility permissions:")
                print("1. Open System Settings → Privacy & Security → Accessibility")
                print("2. Add Terminal (or your Python IDE) to the list")
                print("3. Enable the checkbox next to it")
                print("4. You may need to restart Terminal after granting permissions")
            raise
    
    def run(self):
        if not self.connect():
            return
        
        print("\n=== Mouse Tracking Mode ===")
        print("Your mouse movements are now being sent to the server")
        print("Right-click to stop tracking")
        print("Press Ctrl+C to exit\n")
        
        self.running = True
        self.start_mouse_listener()
        
        try:
            self.mouse_listener.join()
        except KeyboardInterrupt:
            print("\nStopping mouse tracking...")
        finally:
            self.disconnect()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        host = sys.argv[1]
        print(f"Connecting to server at {host}")
        client = MouseClient(host=host)
    else:
        host = input("Enter server IP address (default: localhost): ").strip()
        if not host:
            host = 'localhost'
        client = MouseClient(host=host)
    
    client.run()