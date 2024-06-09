import json
import pymysql
import boto3
from botocore.exceptions import ClientError


def get_secret():
    secret_name = 'sionpoKeys'
    region_name = 'us-east-2'

    session = boto3.session.Session()
    client = session.client(
        service_name='secretmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)
    except ClientError as e:
        raise Exception(f"Error retrieving secret {secret_name}: {str(e)}")


secrets = get_secret()

host = secrets['host']
name = secrets['username']
password = secrets['password']
db_name = "SIONPO"


def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))
    pokemon_id = body.get("id_pokemon")
    updated_data = body.get("updated_data", {})

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