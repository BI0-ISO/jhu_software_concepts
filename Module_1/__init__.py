# from flask import Flask

# app = Flask(__name__)

# @app.route("/")
# def home():
#     return "Mamba Wamba Rocks My Socks Off!"

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=8000, debug=True)

from flask import Flask

def create_app():
    app = Flask(__name__)

    # Import blueprint here, inside the function to avoid circular imports
    from Module_1.board.pages import bp
    app.register_blueprint(bp)

    return app
