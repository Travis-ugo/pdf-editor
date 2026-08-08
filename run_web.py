#!/usr/bin/env python3
from pdf_duplicator.web import run_server

if __name__ == "__main__":
    import socket
    port = 5000
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", 5000)) == 0:
            port = 5050

    print(f"Launching PDF Duplicator Apple HIG Web UI on http://127.0.0.1:{port} ...")
    run_server(host="127.0.0.1", port=port, debug=True)

