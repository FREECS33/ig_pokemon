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
                    "body": json.dumps("Access Denied: Insufficient permits")
                }
        except jwt.DecodeError:
            return {
                "statusCode": 400,
                "body": json.dumps("Invalid token")
            }
        except jwt.ExpiredSignatureError:
            return {
                "statusCode": 401,
                "body": json.dumps("Token has expired")
            }
        except jwt.InvalidTokenError as e:
            return {
                "statusCode": 401,
                "body": json.dumps(f"Invalid token: {str(e)}")
            }
        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps(f"Internal server error: {str(e)}")
            }

        secrets = get_secret()

        host = secrets.get('host')
        name = secrets.get('username')
        password = secrets.get('password')
        db_name = "SIONPO"

        if not all([host, name, password]):
            raise Exception({
                "statusCode": 500,
                "body": "One or more secrets are missing"
            })

        try:
            connection = pymysql.connect(
                host=host,
                user=name,
                password=password,
                db=db_name,
                connect_timeout=10
            )

            try:
                body = json.loads(event['body'])
                user_id = body['id_user']
                with connection.cursor() as cursor:
                    query = """
                        SELECT p.*, 
                            u.username AS user_name, 
                            u.photo AS user_photo,
                            i.interaction_type AS user_interaction
                        FROM Pokemon p
                        JOIN Users u ON p.fk_id_user_creator = u.id_user
                        LEFT JOIN Interactions i ON i.Fk_id_pokemon = p.id_pokemon 
                                                 AND i.Fk_id_user = %s
                                                 AND i.interaction_type IN ('like', 'dislike')

                    """
                    cursor.execute(query, (user_id,))
                    result = cursor.fetchall()
                    columns = [column[0] for column in (cursor.description or [])]
                    result = [dict(zip(columns, row)) for row in result]
                response = {
                    "statusCode": 200,
                    "body": json.dumps(result, default=str)
                }
            except Exception as e:
                response = {
                    "statusCode": 500,
                    "body": f"Query execution error: {str(e)}"
                }
            finally:
                connection.close()
        except pymysql.MySQLError as error:
            error_code = error.args[0]
            if error_code == 2003:
                response = {
                    "statusCode": 503,
                    "body": "Cannot connect to database server"
                }
            elif error_code == 1045:
                response = {
                    "statusCode": 401,
                    "body": "Authentication error: Incorrect username or password"
                }
            elif error_code == 1049:
                response = {
                    "statusCode": 404,
                    "body": "Database not found"
                }
            else:
                response = {
                    "statusCode": 500,
                    "body": f"Database connection error: {str(error)}"
                }
    except Exception as e:
        if isinstance(e.args[0], dict) and 'statusCode' in e.args[0]:
            response = e.args[0]
        else:
            response = {
                "statusCode": 500,
                "body": f"Error: {str(e)}"
            }

    return response
