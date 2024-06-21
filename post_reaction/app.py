import json
import pymysql
import boto3
from botocore.exceptions import ClientError

def get_secret():
    secret_name = 'sionpoKeys'
    region_name = 'us-east-2'

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
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

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        fk_id_user = body.get('Fk_id_user')
        fk_id_pokemon = body.get('Fk_id_pokemon')
        interaction_type = body.get('interaction_type')

        if not fk_id_user or not fk_id_pokemon or not interaction_type:
            raise ValueError("Missing required fields")

        if interaction_type not in ['like', 'dislike', 'favorite']:
            raise ValueError("Invalid interaction_type")
    except (json.JSONDecodeError, ValueError) as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)})
        }

    try:
        secrets = get_secret()
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Error retrieving secrets", "error": str(e)})
        }

    host = secrets['host']
    name = secrets['username']
    password = secrets['password']
    db_name = "SIONPO"

    try:
        connection = pymysql.connect(
            host=host,
            user=name,
            password=password,
            db=db_name,
            connect_timeout=5
        )
    except pymysql.MySQLError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Error connecting to the database", "error": str(e)})
        }

    try:
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
    except Exception as e:
        response = {
            "statusCode": 500,
            "body": json.dumps({"message": "An unexpected error occurred", "error": str(e)})
        }
    finally:
        connection.close()

    return response
