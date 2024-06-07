import json
import pymysql

from secrets_manager import get_secret

secret_name = "sionpoKeys"


def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))
    pokemon_id = body.get("id_pokemon")
    updated_data = body.get("updated_data", {})

    secret = get_secret(secret_name)
    connection = pymysql.connect(
        host=secret['host'],
        user=secret['username'],
        password=secret['password'],
        db='SIONPO',
        connect_timeout=5
    )

    try:
        with connection.cursor() as cursor:
            update_query = "UPDATE Pokemon SET "
            update_query += ", ".join([f"{key}=%s" for key in updated_data.keys()])
            update_query += " WHERE id_pokemon=%s"

            update_values = list(updated_data.values()) + [pokemon_id]

            cursor.execute(update_query, tuple(update_values))
            connection.commit()

        response = {
            "statusCode": 200,
            "body": json.dumps({"message": "Pokemon updated successfully"})
        }
    except pymysql.MySQLError as error:
        response = {
            "statusCode": 500,
            "body": json.dumps({"message": str(error)})
        }
    finally:
        connection.close()

    return response