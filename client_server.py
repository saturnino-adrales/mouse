import socket
import sys
import threading
import time
import json
from pynput import mouse
import tkinter as tk

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
        
        # Screen dimensions
        self.client_width, self.client_height = self.get_screen_size()
        self.server_width = None
        self.server_height = None
        
        # Control state
        self.server_has_control = False
        self.last_y = 0
        self.mouse_controller = mouse.Controller()
        
        # Thread for receiving server messages
        self.receive_thread = None
        
        print(f"[CLIENT] Screen size: {self.client_width}x{self.client_height}")
    
    @staticmethod
    def get_screen_size():
        root = tk.Tk()
        width = root.winfo_screenwidth()
        height = root.winfo_screenheight()
        root.destroy()
        return width, height
        
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"[CLIENT] Connected to server at {self.host}:{self.port}")
            
            # Start receiver thread
            self.receive_thread = threading.Thread(target=self.receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            # Wait for server screen info
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"[CLIENT] Failed to connect to server: {e}")
            return False
    
    def receive_messages(self):
        """Receive messages from server in a separate thread"""
        try:
            buffer = ""
            while self.running:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                buffer += data
                lines = buffer.split('\n')
                buffer = lines[-1]  # Keep incomplete line in buffer
                
                for line in lines[:-1]:
                    if line.strip():
                        self.handle_server_message(line.strip())
        except Exception as e:
            if self.running:
                print(f"[CLIENT] Error receiving messages: {e}")
    
    def handle_server_message(self, message_string):
        try:
            message = json.loads(message_string)
            
            if message.get('type') == 'screen_info':
                self.server_width = message.get('width')
                self.server_height = message.get('height')
                print(f"[CLIENT] Received server screen info: {self.server_width}x{self.server_height}")
                
            elif message.get('type') == 'return_control':
                # Server is returning control to client
                y = message.get('y', self.last_y)
                self.server_has_control = False
                # Place mouse at left edge of client screen
                self.mouse_controller.position = (0, y)
                print(f"[CLIENT] Control returned from server, mouse at (0, {y})")
                
        except json.JSONDecodeError:
            print(f"[CLIENT] Invalid JSON message from server: {message_string}")
    
    def send_message(self, message):
        try:
            if isinstance(message, dict):
                message = json.dumps(message)
            if not message.endswith('\n'):
                message += '\n'
            self.socket.send(message.encode('utf-8'))
            return True
        except Exception as e:
            print(f"[CLIENT] Failed to send message: {e}")
            return False
    
    def send_coordinates(self, coordinates):
        return self.send_message(coordinates)
    
    def disconnect(self):
        self.running = False
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.socket:
            self.socket.close()
            print("[CLIENT] Disconnected from server")
    
    def on_move(self, x, y):
        if not self.running:
            return
        
        self.last_y = y
        
        # Check if mouse is at left edge (x=0 or very close)
        if x <= 2 and not self.server_has_control:
            # Mouse is entering server screen
            self.server_has_control = True
            
            # Send enter message to server
            enter_msg = {'type': 'mouse_enter', 'y': y}
            self.send_message(enter_msg)
            print(f"[CLIENT] Mouse entering server screen at y={y}")
            
            # Hide mouse on client (it's now on server)
            # Note: pynput doesn't have a hide cursor feature, so we'll track state
            
        # If server has control, send all coordinates
        if self.server_has_control:
            # Calculate server coordinates (mouse continues from where it left)
            # Since we're at x=0 on client, server should continue from its right edge
            # We track relative movement from entry point
            
            coordinates = f"{int(x)},{int(y)}"
            if self.send_coordinates(coordinates):
                self.coordinate_count += 1
                
                # Print periodically
                current_time = time.time()
                if self.coordinate_count % 10 == 0 or (current_time - self.last_print_time) >= 0.5:
                    status = "SERVER CONTROL" if self.server_has_control else "CLIENT CONTROL"
                    print(f"[CLIENT] [{status}] Sent: {coordinates} (Total: {self.coordinate_count})")
                    self.last_print_time = current_time
    
    def on_click(self, x, y, button, pressed):
        if pressed and button == mouse.Button.right:
            print("[CLIENT] Right click detected - stopping mouse tracking")
            self.running = False
            return False
    
    def start_mouse_listener(self):
        self.mouse_listener = mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click
        )
        self.mouse_listener.start()
    
    def run(self):
        if not self.connect():
            return
        
        print("\n=== Multi-Screen Mouse Mode ===")
        print("Server screen is on the LEFT of your screen")
        print("Move mouse to LEFT edge (x=0) to control server screen")
        print("Mouse will return when reaching right edge of server")
        print("Right-click to stop tracking")
        print("Press Ctrl+C to exit\n")
        
        self.running = True
        self.start_mouse_listener()
        
        try:
            self.mouse_listener.join()
        except KeyboardInterrupt:
            print("\n[CLIENT] Stopping mouse tracking...")
        finally:
            self.disconnect()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        host = sys.argv[1]
        print(f"[CLIENT] Connecting to server at {host}")
        client = MouseClient(host=host)
    else:
        host = input("Enter server IP address (default: localhost): ").strip()
        if not host:
            host = 'localhost'
        client = MouseClient(host=host)
    
    client.run()