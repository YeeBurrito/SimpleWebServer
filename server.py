import socket
import threading
import argparse
import gzip
import time
import dotenv
import os

def main():
    print("Program started...")

    parser = argparse.ArgumentParser(description="Simple HTTP Server for MC Server Launching")
    parser.add_argument("--directory", "-d", help="Directory to serve files from", default="./files/")
    args = parser.parse_args()

    dotenv.load_dotenv()

    server = Server(directory=args.directory)
    server.start()

class Server:
    def __init__(self, directory):
        self.server_socket = socket.create_server(("10.0.0.106", 4221))
        self.directory = directory
        self.sessions = {}

    def start(self):
        while True:
            sock, addr = self.server_socket.accept()
            threading.Thread(target=self.handle_client, args=(sock, addr)).start()
    
    def stop(self):
        print("Stopping server...")
        self.server_socket.close()
    
    def handle_client(self, sock, addr):
        print(f"Client connected from {addr}")
        # Receive the request from the client
        while True:
            data = sock.recv(1024).decode()
            if not data:
                break
            self.handle_request(sock, data, addr)
        # Send an ok message to the client
        self.send_response(sock, code="200 OK")
    
    def handle_request(self, sock, request, addr):
        print(f"Received request: {request}")
        lines = request.split("\r\n")
        command, path, _ = lines[0].split(" ")
        print(f"Command: {command}, Path: {path}")

        # Print debug info, the addr and if it is authenticated
        print(f"Addr: {addr}")
        print(f"Authenticated: {self.is_authenticated(addr)}")
        print(f"Sessions: {self.sessions}")

        if not self.is_authenticated(addr):
            if path == "/login" and command == "POST":
                self.handle_login_request(sock, lines, addr)
            else:
                self.serve_login_page(sock)
        
        else:
            if command == "GET":
                self.handle_get_request(sock, path, lines)
            elif command == "POST":
                self.handle_post_request(sock, path, lines)
            else:
                self.send_response(sock, code="400 Bad Request")
    
    def handle_get_request(self, sock, path, lines):
        print(f"Handling GET request for path: {path}")
        encoding = self.get_encoding(lines)

        if path == "/":
            path = "/index.html"
        try:
            with open(f"{self.directory}{path}", "rb") as f:
                data = f.read()
                self.send_response(sock, code="200 OK", data=data, encoding=encoding)
        except FileNotFoundError:
            self.send_response(sock, code="404 Not Found")
    
    def handle_post_request(self, sock, path, lines):
        print(f"Handling POST request for path: {path}")
        data = lines[-1]
        print(f"Data: {data}")

        if path.startswith("/files/"):
            file_path = self.directory + path[7:]
            with open(file_path, "wb") as f:
                f.write(data.encode())
            self.send_response(sock, code="201 Created")
        else:
            self.send_response(sock, code="404 Not Found")
    
    def handle_login_request(self, client_socket, request_lines, client_address):
        """Handle a login request."""
        credentials = request_lines[-1]
        username, password = self.parse_credentials(credentials)
        if self.authenticate(username, password):
            self.sessions[client_address] = time.time()
            self.serve_index_page(client_socket)
        else:
            self.serve_login_page(client_socket)
    
    def serve_login_page(self, client_socket):
        """Serve the login page to the client."""
        with open("./files/login.html", "r") as f:
            data = f.read()
        self.send_response(client_socket, code="200 OK", data=data)
    
    def serve_index_page(self, client_socket):
        """Serve the index page to the client."""
        with open("./files/index.html", "r") as f:
            data = f.read()
        self.send_response(client_socket, code="200 OK", data=data)
    
    def get_encoding(self, request_lines):
        for line in request_lines:
            if line.startswith("Accept-Encoding: "):
                encodings = line.split(": ")[1].split(", ")
                if "gzip" in encodings:
                    return "gzip"
        return None
    
    def send_response(self, client_socket, code, headers=None, data=None, encoding=None):
        """Send an HTTP response to the client."""
        response = f"HTTP/1.1 {code}\r\n"
        
        if encoding:
            pass
            # response += f"Content-Encoding: {encoding}\r\n"
            # if encoding == "gzip" and data and not isinstance(data, bytes):
            #     data = gzip.compress(data.encode())
        
        if headers:
            for header in headers:
                response += f"{header}\r\n"
        
        if data:
            response += f"Content-Length: {len(data)}\r\n"
        
        response += "\r\n"
        
        if data:
            response = response.encode() + data if isinstance(data, bytes) else response.encode() + data.encode()
        else:
            response = response.encode()

        print(f"Sending response: {response}")
        client_socket.send(response)

    def is_authenticated(self, client_address):
        """Check if the client is authenticated."""
        return client_address in self.sessions

    def parse_credentials(self, data):
        """Parse the username and password from the POST data."""
        params = data.split("&")
        username = params[0].split("=")[1]
        password = params[1].split("=")[1]
        return username, password

    def authenticate(self, username, password):
        """Authenticate the user credentials."""
        print(f"Authenticating user: {username}")
        print(f"Authenticating password: {password}")
        print(f"Env username: {os.getenv('WEB_USER')}")
        print(f"Env password: {os.getenv('PASSWORD')}")
        return username == os.getenv("WEB_USER") and password == os.getenv("PASSWORD")
    
    #Handle any keyboard interrupts
    def __del__(self):
        self.stop()
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
    
if __name__ == "__main__":
    main()
