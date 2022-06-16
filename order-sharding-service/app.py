from flask import Flask
from flask import request as flask_request

app = Flask("order-sharding-service")

@app.get('/test')
def test_get2():
    print("running", file=sys.stderr)
    return "test", 200
