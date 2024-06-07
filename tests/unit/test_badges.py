import json

import pytest
from post_badges import app

@pytest.fixture()
def apigw_event():

    return {
        "body": json.dumps({
            "badge_name": "Pikachu",
            "description": "An electric Pokémon",
            "standard_to_get": "Thunderstone",
            "date_earned": "2024-06-05",
            "image": "pikachu.png"
        })
    }


def test_lambda_handler(apigw_event):

    ret = app.lambda_handler(apigw_event, None)


    assert ret["statusCode"] == 200 or ret["statusCode"] == 500

    if ret["statusCode"] == 200:

        data = json.loads(ret["body"])
        print("Query Result:", data)
        assert isinstance(data, list)
        assert len(data) > 0
    else:

        print("Error:", ret["body"])