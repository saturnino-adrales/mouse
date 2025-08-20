import socket
import sys

class MouseClient:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.socket = None
        
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
        if self.socket:
            self.socket.close()
            print("Disconnected from server")
    
    def run(self):
        if not self.connect():
            return
            
        print("Enter coordinates in format 'x,y' (e.g., '100,200')")
        print("Type 'quit' to exit")
        
        try:
            while True:
                user_input = input("Coordinates: ").strip()
                
                if user_input.lower() == 'quit':
                    break
                
                if not user_input:
                    continue
                    
                try:
                    x, y = map(int, user_input.split(','))
                    if self.send_coordinates(user_input):
                        print(f"Sent coordinates: {x}, {y}")
                    else:
                        break
                except ValueError:
                    print("Invalid format. Please use 'x,y' format (e.g., '100,200')")
                    
        except KeyboardInterrupt:
            print("\nExiting...")
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