import http.server
import socketserver
import json
from pathlib import Path

PORT = 8080

class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/data":
            # Load all JSON data
            data = {}
            project_dir = Path(__file__).resolve().parent
            results_dir = project_dir / "data" / "results"
            quality_dir = project_dir / "data" / "quality"
            
            # Load metrics
            for phase in ["baseline", "corrupted", "repaired"]:
                path = results_dir / f"{phase}_metrics.json"
                if path.exists():
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            data[f"{phase}_metrics"] = json.load(f)
                    except Exception as e:
                        data[f"{phase}_metrics"] = {"error": str(e)}
                else:
                    data[f"{phase}_metrics"] = None
                    
            # Load quality checks
            for phase in ["baseline", "corrupted", "repaired"]:
                path = quality_dir / f"{phase}_quality.json"
                if path.exists():
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            data[f"{phase}_quality"] = json.load(f)
                    except Exception as e:
                        data[f"{phase}_quality"] = {"error": str(e)}
                else:
                    data[f"{phase}_quality"] = None
                    
            # Load corruption log
            corrupted_log_path = results_dir / "corruption_log.json"
            if corrupted_log_path.exists():
                try:
                    with open(corrupted_log_path, "r", encoding="utf-8") as f:
                        data["corruption_log"] = json.load(f)
                except Exception as e:
                    data["corruption_log"] = {"error": str(e)}
            else:
                data["corruption_log"] = None

            # Respond with JSON
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            
        elif self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            
            # Read and serve the index.html
            project_dir = Path(__file__).resolve().parent
            html_path = project_dir / "src" / "observability" / "dashboard.html"
            if html_path.exists():
                html_content = html_path.read_text(encoding="utf-8")
            else:
                html_content = f"<h1>Dashboard HTML template not found at {html_path}</h1>"
            self.wfile.write(html_content.encode("utf-8"))
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found")

def run():
    # Allow address reuse to avoid "Address already in use" errors during quick restarts
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print("==================================================")
        print(f"RAG Data Observability Dashboard is running!")
        print(f"URL: http://localhost:{PORT}")
        print("Press Ctrl+C to stop the server.")
        print("==================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")

if __name__ == "__main__":
    run()
