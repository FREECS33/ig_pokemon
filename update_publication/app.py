import json
import pymysql
import boto3


def get_secret(secret_name):
    region_name = 'us-east-2'
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret = response['SecretString']
        return json.loads(secret)
    except Exception as e:
        raise Exception(f"Error retrieving secret {secret_name}: {str(e)}")


def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))
    pokemon_id = body.get("id_pokemon")
    updated_data = body.get("updated_data", {})

    secrets = get_secret('sionpoKeys')
    connection = pymysql.connect(
        host=secrets['host'],
        user=secrets['username'],
        password=secrets['password'],
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
