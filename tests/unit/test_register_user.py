import json
import pytest
from register_user import app


@pytest.fixture()
def apigw_event():
    return {
        "username": "testuser",
        "password": "TestPassword123!",
        "email": "testuser@example.com",
        "picture": "https://example.com/profile.jpg"
    }


def test_lambda_handler(apigw_event):
    ret = app.lambda_handler(apigw_event, None)

    assert ret["statusCode"] == 200 or ret["statusCode"] == 400

    if ret["statusCode"] == 200:
        data = json.loads(ret["body"])
        print("Registration Result:", data)
        assert "message" in data and data["message"] == "User registration successful"
    else:
        print("Error:", ret["body"])
        assert "error" in json.loads(ret["body"])
