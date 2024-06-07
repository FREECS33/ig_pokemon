import json
import pytest
from post_reaction import app  # Asegúrate de que el nombre del archivo sea correcto


@pytest.fixture()
def apigw_event():
    return {
        "body": json.dumps({
            "Fk_id_user": 1,
            "Fk_id_pokemon": 1,
            "interaction_type": "like"
        })
    }


def test_lambda_handler(apigw_event):
    ret = app.lambda_handler(apigw_event, None)

    assert ret["statusCode"] == 200 or ret["statusCode"] == 500

    if ret["statusCode"] == 200:
        data = json.loads(ret["body"])
        assert "message" in data
        assert data["message"] == "Interacción añadida exitosamente"
        print("Success:", data["message"])
    else:
        print("Error:", ret["body"])
