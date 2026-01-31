from Module_1 import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",  # or "127.0.0.1"
        port=8080,
        debug=True
    )
