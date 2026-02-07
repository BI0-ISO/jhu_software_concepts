from flask import Flask
from M1_material.board import bp as m1_bp
from M3_material.board import bp as m3_bp

app = Flask(__name__)

# Register both blueprints
app.register_blueprint(m1_bp)
app.register_blueprint(m3_bp)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
