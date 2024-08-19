import json
import pymysql
import boto3
import jwt
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


def lambda_handler(event, context):
    """
    token = event['headers']['Authorization'].split(' ')[1]
    decoded_token = jwt.decode(token, options={"verify_signature": False})

    user_groups = decoded_token.get('cognito:groups', [])

    if "user" not in user_groups and "mod" not in user_groups:
        raise Exception({
            "statusCode": 403,
            "body": json.dumps("Access Denied: Insufficient permits")
        })
    """
    try:
        secrets = get_secret()
    except Exception as e:
        return {
            "statusCode": 403,
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
            "body": json.dumps(f"Database integrity error: {str(e)}")
        }
    except pymysql.OperationalError as e:
        return {
            "statusCode": 503,
            "body": json.dumps(f"Database connection error: {str(e)}")
        }
    except pymysql.MySQLError as e:
        return {
            "statusCode": 500,
            "body": json.dumps(f"Database error: {str(e)}")
        }

    try:
        body = json.loads(event['body'])
        email = body['email']

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    id_user, 
                    username, 
                    password, 
                    photo
                FROM Users 
                WHERE email = %s
            """, (email,))
            user_info = cursor.fetchone()

            if user_info:
                response_data = {
                    "id_user": user_info[0],
                    "username": user_info[1],
                    "password": user_info[2],
                    "photo": user_info[3],
                }

                response = {
                    "statusCode": 200,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS,PUT,DELETE',
                        'Access-Control-Allow-Headers': 'Content-Type,Authorization'
                    },
                    "body": json.dumps(response_data, default=str)
                }
            else:
                response = {
                    "statusCode": 404,
                    "body": json.dumps("User not found")
                }

    except KeyError as e:
        response = {
            "statusCode": 400,
            "body": json.dumps(f"Missing key in request body: {str(e)}")
        }

    except pymysql.IntegrityError as e:
        response = {
            "statusCode": 422,
            "body": json.dumps(f"Database integrity error: {str(e)}")
        }

    except pymysql.OperationalError as e:
        response = {
            "statusCode": 503,
            "body": json.dumps(f"Database connection error: {str(e)}")
        }

    except pymysql.MySQLError as e:
        response = {
            "statusCode": 500,
            "body": json.dumps(f"Database error: {str(e)}")
        }

    except Exception as e:
        response = {
            "statusCode": 403,
            "body": json.dumps(str(e))
        }

    finally:
        connection.close()

    return response
