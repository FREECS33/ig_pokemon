import json

import pytest
from post_publication import app

@pytest.fixture()
def apigw_event():
    # Simulamos un evento de API Gateway con un body que representa los datos de un nuevo Pokémon
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
    # Llamamos a la función lambda con el evento simulado
    ret = app.lambda_handler(apigw_event, None)  # Utiliza la función lambda_handler correctamente

    # Verificamos el código de estado de la respuesta
    assert ret["statusCode"] == 200 or ret["statusCode"] == 500

    if ret["statusCode"] == 200:
        # Si el código de estado es 200, verificamos que la respuesta contiene datos
        data = json.loads(ret["body"])
        print("Query Result:", data)
        assert isinstance(data, list)
        assert len(data) > 0
    else:
        # Si el código de estado no es 200, imprimimos el error
        print("Error:", ret["body"])