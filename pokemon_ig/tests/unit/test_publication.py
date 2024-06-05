import json
import pymysql
import pytest
from unittest.mock import patch
from post_publication import app

# Configura los detalles de la base de datos de prueba
TEST_DB_HOST = "sionpo.clouqoguo4hz.us-east-2.rds.amazonaws.com"
TEST_DB_NAME = "SIONPO"
TEST_DB_USER = "admin"
TEST_DB_PASSWORD = "sionpo2024"

@pytest.fixture()
def apigw_event():
    return {
        "body": json.dumps({
            "pokemon_name": "Pikachu",
            "abilities": "Static, Lightning Rod",
            "types": "Electric",
            "description": "A yellow electric type Pokémon.",
            "evolutions_conditions": "Thunder Stone",
            "image": "http://example.com/pikachu.png",
            "likes_count": 100,
            "dislikes_count": 10,
            "creation_update_date": "2024-06-05",
            "id_pokemon": 25,
            "fk_id_user": 1
        })
    }

@patch('insert_pokemon.pymysql.connect')
def test_lambda_handler(mock_connect, apigw_event):
    # Configurar el mock para la conexión a la base de datos
    mock_connection = mock_connect.return_value
    mock_cursor = mock_connection.cursor.return_value

    # Configurar los resultados de la base de datos simulada
    mock_cursor.fetchall.return_value = [{
        "Name": "Pikachu",
        "Abilities": "Static, Lightning Rod",
        "Types": "Electric",
        "Description": "A yellow electric type Pokémon.",
        "EvolutionsConditions": "Thunder Stone",
        "Image": "http://example.com/pikachu.png",
        "LikesCount": 100,
        "DislikesCount": 10,
        "CreationUpdateDate": "2024-06-05",
        "IdPokemon": 25,
        "FkIdUser": 1
    }]

    # Llamar a la función lambda_handler con el evento simulado
    response = app.lambda_hanlder(apigw_event, "")

    # Verificar el código de estado y el contenido de la respuesta
    assert response["statusCode"] == 200

    body = json.loads(response["body"])
    assert isinstance(body, list)
    assert len(body) > 0

    # Verificar que los datos retornados sean los esperados
    assert body[0]["Name"] == "Pikachu"
    assert body[0]["Abilities"] == "Static, Lightning Rod"

    # Verificar que las llamadas a la base de datos fueron hechas correctamente
    mock_cursor.execute.assert_called()
    mock_connection.commit.assert_called()
    mock_connection.close.assert_called()
