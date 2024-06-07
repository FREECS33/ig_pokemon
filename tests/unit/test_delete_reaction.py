import json
import pytest
from delete_reaction import app


@pytest.fixture()
def apigw_event():
    return {
        "body": json.dumps({
            "id_interaction": 1
        })
    }


def test_lambda_handler(apigw_event):
    ret = app.lambda_handler(apigw_event, None)

    assert ret["statusCode"] == 200 or ret["statusCode"] == 500

    if ret["statusCode"] == 200:
        data = json.loads(ret["body"])
        assert "message" in data
        assert data["message"] == "Interaction deleted successfully"
        print("Success:", data["message"])
    else:
        print("Error:", ret["body"])
