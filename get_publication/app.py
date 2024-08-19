import json
import pymysql
import boto3
import jwt
from jwt import PyJWKClient
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError


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
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            response = {
                "statusCode": 404,
                "body": f"Secret {secret_name} not found"
            }
        elif error_code == 'InvalidRequestException':
            response = {
                "statusCode": 400,
                "body": f"Invalid request for secret {secret_name}"
            }
        elif error_code == 'InvalidParameterException':
            response = {
                "statusCode": 400,
                "body": f"Invalid parameter for secret {secret_name}"
            }
        elif error_code == 'AccessDeniedException':
            response = {
                "statusCode": 403,
                "body": f"Access denied for secret {secret_name}"
            }
        else:
            response = {
                "statusCode": 500,
                "body": f"Error retrieving secret {secret_name}: {str(e)}"
            }
        raise Exception(response)
    except NoCredentialsError:
        raise Exception({
            "statusCode": 401,
            "body": "AWS credentials not found"
        })
    except PartialCredentialsError:
        raise Exception({
            "statusCode": 401,
            "body": "Incomplete AWS credentials"
        })
    except Exception as e:
        raise Exception({
            "statusCode": 500,
            "body": f"Unknown error: {str(e)}"
        })


keys_url = "https://cognito-idp.us-east-2.amazonaws.com/us-east-2_NDXZOG7DQ/.well-known/jwks.json"


def lambda_handler(event, context):
    try:
        if "headers" not in event or "Authorization" not in event["headers"]:
            return {
                "statusCode": 400,
                "body": json.dumps("Authorization header is missing")
            }
        auth_header = event["headers"]["Authorization"]

        if not auth_header.startswith("Bearer "):
            return {
                "statusCode": 400,
                "body": json.dumps("Authorization header must start with 'Bearer '")
            }

        token = auth_header.split(' ')[1]

        jwt_client = PyJWKClient(keys_url)

        public_key = jwt_client.get_signing_key_from_jwt(token)

        decoded_token = jwt.decode(token, key=public_key, algorithms=["RS256"])

        user_groups = decoded_token.get('cognito:groups', [])

        if "user" not in user_groups and "mod" not in user_groups:
            return {
                "statusCode": 403,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization'
                },
                "body": json.dumps("Access Denied: Insufficient permits")
            }
    except jwt.DecodeError:
        return {
            "statusCode": 400,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            "body": json.dumps("Invalid token")
        }
    except jwt.ExpiredSignatureError:
        return {
            "statusCode": 401,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            "body": json.dumps("Token has expired")
        }
    except jwt.InvalidTokenError as e:
        return {
            "statusCode": 401,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            "body": json.dumps(f"Invalid token: {str(e)}")
        }
    except Exception as e:
        return {
            "statusCode": 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            "body": json.dumps(f"Internal server error: {str (e)}")
        }

    try:
        secrets = get_secret()
    except Exception as e:
        return {
            "statusCode": 403,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            "body": json.dumps(f"Error retrieving secret: {str(e)}")
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
    except pymysql.IntegrityError as e:
        return {
            "statusCode": 422,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            "body": json.dumps(f"Database integrity error: {str(e)}")
        }
    except pymysql.OperationalError as e:
        return {
            "statusCode": 503,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            "body": json.dumps(f"Database connection error: {str(e)}")
        }
    except pymysql.MySQLError as e:
        return {
            "statusCode": 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            "body": json.dumps(f"Database error: {str(e)}")
        }

    try:
        with connection.cursor() as cursor:
            id_pokemon = event['queryStringParameters']['id_pokemon']
            cursor.execute("SELECT * FROM Pokemon WHERE id_pokemon = %s", (id_pokemon,))
            result = cursor.fetchone()

            if result:
                columns = [desc[0] for desc in cursor.description]
                result_dict = dict(zip(columns, result))
            else:
                result_dict = {}

        response = {
            "statusCode": 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            "body": json.dumps(result_dict, default=str)
        }

    except KeyError as e:
        response = {
            "statusCode": 400,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            "body": json.dumps(f"Missing key in request body: {str(e)}")
        }

    except pymysql.IntegrityError as e:
        response = {
            "statusCode": 422,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            "body": json.dumps(f"Database integrity error: {str(e)}")
        }

    except pymysql.OperationalError as e:
        response = {
            "statusCode": 503,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            "body": json.dumps(f"Database connection error: {str(e)}")
        }

    except pymysql.MySQLError as e:
        response = {
            "statusCode": 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            "body": json.dumps(f"Database error: {str(e)}")
        }

    except Exception as e:
        response = {
            "statusCode": 403,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            "body": json.dumps(str(e))
        }

    finally:
        connection.close()

    return response
