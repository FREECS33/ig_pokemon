import json
import pymysql

from secrets_manager import get_secret

secret_name = "sionpoKeys"


def lambda_handler(event, context):
    try:
        secret = get_secret(secret_name)
        connection = pymysql.connect(
            host=secret['host'],
            user=secret['username'],
            password=secret['password'],
            db='SIONPO',
            connect_timeout=5
        )

    except pymysql.MySQLError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Error connecting to the database", "error": str(e)})
        }

    try:
        body = json.loads(event['body'])
        fk_id_user = body['Fk_id_user']
        fk_id_pokemon = body['Fk_id_pokemon']
        interaction_type = body['interaction_type']

        if not fk_id_user or not fk_id_pokemon or not interaction_type:
            raise ValueError("Missing required fields")

        if interaction_type not in ['like', 'dislike', 'favorite']:
            raise ValueError("Invalid interaction_type")

        with connection.cursor() as cursor:
            sql = """
            INSERT INTO Interactions (Fk_id_user, Fk_id_pokemon, interaction_type)
            VALUES (%s, %s, %s)
            """
            cursor.execute(sql, (fk_id_user, fk_id_pokemon, interaction_type))
            connection.commit()

        response = {
            "statusCode": 200,
            "body": json.dumps({"message": "Interacción añadida exitosamente"})
        }
    except pymysql.MySQLError as error:
        response = {
            "statusCode": 500,
            "body": json.dumps({"message": "Database error", "error": str(error)})
        }
    except json.JSONDecodeError as json_error:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": "Invalid JSON format", "error": str(json_error)})
        }
    except ValueError as ve:
        response = {
            "statusCode": 400,
            "body": json.dumps({"message": str(ve)})
        }
    except Exception as e:
        response = {
            "statusCode": 500,
            "body": json.dumps({"message": "An unexpected error occurred", "error": str(e)})
        }
    finally:
        connection.close()

    return response
