#!/usr/bin/env python3
from pdf_duplicator.web import run_server

if __name__ == "__main__":
    print("Launching PDF Duplicator Apple HIG Web UI...")
    run_server(host="127.0.0.1", port=5000, debug=True)
