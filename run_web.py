#!/usr/bin/env python3
from pdf_duplicator.web import run_server

if __name__ == "__main__":
    import os
    import socket

    port_env = os.environ.get("PORT")
    if port_env:
        port = int(port_env)
    else:
        port = 5000
        for p in range(5050, 5100):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("127.0.0.1", p)) != 0:
                    port = p
                    break
        os.environ["PORT"] = str(port)

    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        print(f"Launching PDF Duplicator Apple HIG Web UI on http://127.0.0.1:{port} ...")

    run_server(host="127.0.0.1", port=port, debug=True)



