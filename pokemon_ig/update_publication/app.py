import json
import pymysql

host = "sionpo.clouqoguo4hz.us-east-2.rds.amazonaws.com"
name = "admin"
password = "sionpo2024"
db_name = "SIONPO"


def lambda_handler(event, context):
    pokemon_id = event.get("id_pokemon")
    updated_data = event.get("updated_data", {})

    connection = pymysql.connect(
        host=host,
        user=name,
        password=password,
        db=db_name,
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
            "body": "Pokemon updated successfully"
        }
    except pymysql.MySQLError as error:
        response = {
            "statusCode": 500,
            "body": str(error)
        }
    finally:
        connection.close()

    return response
