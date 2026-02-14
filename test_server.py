from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "Server is working!"

@app.route("/test")
def test():
    return jsonify({"status": "OK", "message": "Flask is running"})

if __name__ == "__main__":
    print("Starting test server on http://localhost:3000")
    app.run(debug=True, port=3000, host='0.0.0.0')
    