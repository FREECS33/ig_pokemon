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
        raise Exception(f"Error retrieving secret: {e.response['Error']['Message']}")


def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        if "id_pokemon" not in body:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Missing id_pokemon in body"})
            }
        id_pokemon = body['id_pokemon']
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
            "body": json.dumps({"message": str(e)})
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
    except pymysql.OperationalError as e:
        return {
            "statusCode": 503,
            "body": json.dumps({"message": str(e)})
        }

    try:
        with connection.cursor() as cursor:
            try:
                delete_publication = "DELETE FROM Pokemon WHERE id_pokemon = %s"
                rows_affected_publications = cursor.execute(delete_publication, (id_pokemon,))
                connection.commit()
            except pymysql.MySQLError as e:
                connection.rollback()
                return {
                    "statusCode": 400,
                    "body": json.dumps({"message": str(e)})
                }
            if(rows_affected_publications == 0):
                return {
                    "statusCode": 404,
                    "body": json.dumps({"message": "Pokemon not found"})
                }
            response = {
                "statusCode": 200,
                "body": json.dumps({"message": "Pokemon deleted successfully"})
            }
            return response

    except pymysql.MySQLError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Database error"})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "An unexpected error occurred"})
        }
    finally:
        connection.close()


