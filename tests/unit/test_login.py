import json
import pytest
from login import app


@pytest.fixture()
def apigw_event():
    return {
        "username": "zel",
        "password": "TestPassword123!"
    }


def test_lambda_handler(apigw_event):
    ret = app.lambda_handler(apigw_event, None)

    assert ret["statusCode"] == 200 or ret["statusCode"] == 400

    if ret["statusCode"] == 200:
        data = json.loads(ret["body"])
        print("Login Result:", data)
        assert "message" in data and data["message"] == "User login successful"
        assert "authentication_result" in data
    else:
        print("Error:", ret["body"])
        assert "error" in json.loads(ret["body"])
