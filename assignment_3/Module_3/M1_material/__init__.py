from flask import Flask

def create_app():
    app = Flask(__name__)

    from Module_3.board import bp
    app.register_blueprint(bp)

    return app
