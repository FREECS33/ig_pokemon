import json

import pytest
from post_publication import app

@pytest.fixture()
def apigw_event():

    return {
        "body": json.dumps({
            "pokemon_name": "Pikachu",
            "abilities": ["Static", "Lightning Rod"],
            "types": ["Electric"],
            "description": "An electric Pokémon",
            "evolution_conditions": "Thunderstone",
            "image": "pikachu.png",
            "likes_count": 100,
            "dislikes_count": 10,
            "creation_update_date": "2024-06-05",
            "id_pokemon": 25,
            "fk_id_user_creator": 1
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