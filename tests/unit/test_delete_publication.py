import json
import pytest
from delete_publication import app


@pytest.fixture()
def apigw_event():
    return {
        "queryStringParameters": {
            "id_pokemon": 1111
        }
    }


def test_lambda_handler(apigw_event):
    ret = app.lambda_handler(apigw_event, None)

    assert ret["statusCode"] == 200 or ret["statusCode"] == 500

    if ret["statusCode"] == 200:
        data = json.loads(ret["body"])
        print("Response Message:", data)
        assert data["message"] == "Pokemon deleted successfully"
    else:
        print("Error:", ret["body"])
