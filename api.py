from http.server import BaseHTTPRequestHandler, HTTPServer
import json


class ApiHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/api"):
            payload = {"message": "API is working", "status": "ok"}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode("utf-8"))
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode("utf-8"))

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8000), ApiHandler)
    print("Server running at http://127.0.0.1:8000")
    server.serve_forever()
