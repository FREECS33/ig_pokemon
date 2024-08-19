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

        if "user" not in user_groups:
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
    try:
        body = json.loads(event['body'])
        required_fields = ['pokemon_name', 'abilities', 'types', 'description', 'image']
        for field in required_fields:
            if field not in body:
                raise ValueError(f"Missing required field: {field}")
        pokemon_name = body['pokemon_name']
        abilities = json.dumps(body['abilities'])
        types = json.dumps(body['types'])
        description = body['description']
        evolution_conditions = body['evolution_conditions']
        image = body['image']
        likes_count = body['likes_count']
        dislikes_count = body['dislikes_count']
        creation_update_date = body['creation_update_date']
        fk_id_user_creator = body['fk_id_user_creator']

        if likes_count < 0:
            return {
                "statusCode": 422,
                "body": json.dumps({"message": "likes_count cannot be negative"})
            }
        if dislikes_count < 0:
            return {
                "statusCode": 422,
                "body": json.dumps({"message": "likes_count cannot be negative"})
            }
    except (json.JSONDecodeError, ValueError) as error:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": str(error)})
        }
    try:
        secrets = get_secret()
    except Exception as error:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": str(error)})
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
    except pymysql.MySQLError as error:
        return {
            "statusCode": 500,
            "body": json.dumps(str(error))
        }

    try:
        with connection.cursor() as cursor:
            sql = """
                    INSERT INTO Pokemon (
                        pokemon_name, abilities, types, description, 
                        evolution_conditions, image, likes_count, 
                        dislikes_count, creation_update_date, fk_id_user_creator
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """
            cursor.execute(sql, (
                pokemon_name, abilities, types, description,
                evolution_conditions, image, likes_count,
                dislikes_count, creation_update_date, fk_id_user_creator
            ))
            connection.commit()

        response = {
            "statusCode": 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS,PUT,DELETE',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            "body": json.dumps({"message": "Pokemon created successfully"})
        }

    except pymysql.MySQLError as error:

        response = {
            "statusCode": 500,
            "body": json.dumps(str(error))
        }

    finally:
        connection.close()

    return response
