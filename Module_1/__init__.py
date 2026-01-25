from flask import Flask
from Module_1.board.pages import bp
import os

def create_app():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.dirname(base_dir)

    app = Flask(
        __name__,
        template_folder=os.path.join(project_root, "templates"),
        static_folder=os.path.join(project_root, "static")
    )

    app.register_blueprint(bp)
    return app

# """ from flask import Flask

# def create_app():
#     app = Flask(__name__)

#     # Import blueprint here, inside the function to avoid circular imports
#     from Module_1.board.pages import bp
#     app.register_blueprint(bp)

#     return app
#  """