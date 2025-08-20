import socket
import threading
import netifaces
import time
import json
from pynput.mouse import Button, Listener
from pynput import mouse
import tkinter as tk

class MouseServer:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.mouse_controller = mouse.Controller()
        self.client_counters = {}
        self.screen_width, self.screen_height = self.get_screen_size()
        self.active_control = False  # Whether server is controlling mouse
        print(f"[SERVER] Screen size: {self.screen_width}x{self.screen_height}")
    
    @staticmethod
    def get_screen_size():
        root = tk.Tk()
        width = root.winfo_screenwidth()
        height = root.winfo_screenheight()
        root.destroy()
        return width, height
    
    @staticmethod
    def get_network_interfaces():
        interfaces = {}
        for interface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip = addr['addr']
                    if ip != '127.0.0.1':
                        interfaces[interface] = ip
        return interfaces
    
    @staticmethod
    def select_interface():
        interfaces = MouseServer.get_network_interfaces()
        
        if not interfaces:
            print("No network interfaces found. Using localhost.")
            return 'localhost'
        
        print("\nAvailable network interfaces:")
        print("0. localhost (127.0.0.1)")
        
        interface_list = list(interfaces.items())
        for i, (name, ip) in enumerate(interface_list, 1):
            print(f"{i}. {name}: {ip}")
            if 'bridge' in name.lower():
                print(f"   ^ Thunderbolt Bridge detected")
        
        while True:
            try:
                choice = input("\nSelect interface number (default: 0 for localhost): ").strip()
                if not choice:
                    return 'localhost'
                    
                choice = int(choice)
                if choice == 0:
                    return 'localhost'
                elif 1 <= choice <= len(interface_list):
                    selected_ip = interface_list[choice - 1][1]
                    print(f"Selected: {interface_list[choice - 1][0]} ({selected_ip})")
                    return selected_ip
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")
        
    def handle_client(self, client_socket, address):
        print(f"[SERVER] Connection from {address}")
        client_id = f"{address[0]}:{address[1]}"
        self.client_counters[client_id] = {'count': 0, 'last_print': time.time()}
        
        try:
            # Send screen dimensions to client on connect
            screen_info = {
                'type': 'screen_info',
                'width': self.screen_width,
                'height': self.screen_height
            }
            message = json.dumps(screen_info) + '\n'
            client_socket.send(message.encode('utf-8'))
            print(f"[SERVER] Sent screen info to client: {self.screen_width}x{self.screen_height}")
            
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                    
                lines = data.strip().split('\n')
                for line in lines:
                    if line.strip():
                        self.handle_message(line.strip(), client_id, client_socket)
                        
        except Exception as e:
            print(f"[SERVER] Error handling client {address}: {e}")
        finally:
            if client_id in self.client_counters:
                total = self.client_counters[client_id]['count']
                print(f"[SERVER] Client {address} disconnected. Total coordinates received: {total}")
                del self.client_counters[client_id]
            self.active_control = False
            client_socket.close()
    
    def handle_message(self, message_string, client_id, client_socket):
        try:
            # Try to parse as JSON first
            try:
                message = json.loads(message_string)
                if message.get('type') == 'mouse_enter':
                    # Client mouse is entering server screen from the right
                    self.active_control = True
                    y = message.get('y', 0)
                    # Place mouse at right edge of server screen
                    self.mouse_controller.position = (self.screen_width - 1, y)
                    print(f"[SERVER] Mouse control activated at ({self.screen_width - 1}, {y})")
                    return
                elif message.get('type') == 'mouse_leave':
                    # Mouse is leaving server screen
                    self.active_control = False
                    print(f"[SERVER] Mouse control deactivated")
                    return
            except json.JSONDecodeError:
                # Fall back to coordinate parsing
                pass
            
            # Parse as coordinates
            x, y = map(int, message_string.split(','))
            
            # Only move mouse if server has active control
            if self.active_control:
                self.mouse_controller.position = (x, y)
                
                # Check if mouse is leaving to the right (back to client)
                if x >= self.screen_width - 5:  # Near right edge
                    self.active_control = False
                    # Send control back to client
                    response = json.dumps({'type': 'return_control', 'y': y}) + '\n'
                    client_socket.send(response.encode('utf-8'))
                    print(f"[SERVER] Returning control to client at y={y}")
            
            # Update counter
            if client_id in self.client_counters:
                self.client_counters[client_id]['count'] += 1
                count = self.client_counters[client_id]['count']
                current_time = time.time()
                last_print = self.client_counters[client_id]['last_print']
                
                # Print every 10th coordinate or every 0.5 seconds
                if count % 10 == 0 or (current_time - last_print) >= 0.5:
                    status = "ACTIVE" if self.active_control else "INACTIVE"
                    print(f"[SERVER] [{status}] Received from {client_id}: ({x}, {y}) - Total: {count} coordinates")
                    self.client_counters[client_id]['last_print'] = current_time
        except ValueError:
            print(f"[SERVER] Invalid message format: {message_string}")
    
    def start(self):
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        print(f"Server listening on {self.host}:{self.port}")
        
        try:
            while True:
                client_socket, address = self.socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_client, 
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
        except KeyboardInterrupt:
            print("Server shutting down...")
        finally:
            self.socket.close()

if __name__ == "__main__":
    selected_host = MouseServer.select_interface()
    server = MouseServer(host=selected_host)
    server.start()