import json
import pymysql
import boto3
from botocore.exceptions import ClientError
import jwt
from jwt import PyJWKClient

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


def verify_token(token):
    region = "us-east-2"
    userpool_id = "us-east-2_NDXZOG7DQ"  # Reemplaza con tu User Pool ID
    app_client_id = "5s5c1ofpkq30gkbt61q1hdicfd"  # Reemplaza con tu App Client ID

    jwks_url = f'https://cognito-idp.{region}.amazonaws.com/{userpool_id}/.well-known/jwks.json'
    jwks_client = PyJWKClient(jwks_url)

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        decoded_token = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=app_client_id
        )
        return decoded_token
    except jwt.ExpiredSignatureError:
        raise Exception("Token has expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")


def lambda_handler(event, context):
    # Verificar token de autorización
    try:
        token = event['headers']['Authorization'].split(' ')[1]
        decoded_token = verify_token(token)
    except KeyError:
        return {
            "statusCode": 401,
            "body": json.dumps({"message": "Missing Authorization Header"})
        }
    except Exception as e:
        return {
            "statusCode": 401,
            "body": json.dumps({"message": str(e)})
        }

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
            if rows_affected_publications == 0:
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
