import json
import pytest
from confirm_register import app


@pytest.fixture()
def apigw_event():
    return {
        "username": "zel",
        "confirmation_code": "754981"
    }


def test_lambda_handler(apigw_event):
    ret = app.lambda_handler(apigw_event, None)

    assert ret["statusCode"] == 200 or ret["statusCode"] == 400

    if ret["statusCode"] == 200:
        data = json.loads(ret["body"])
        print("Confirmation Result:", data)
        assert "message" in data and data["message"] == "User account confirmed successfully"
    else:
        print("Error:", ret["body"])
        assert "error" in json.loads(ret["body"])
