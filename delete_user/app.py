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
    token = event['headers']['Authorization'].split(' ')[1]
    decoded_token = jwt.decode(token, options={"verify_signature": False})

    user_groups = decoded_token.get('cognito:groups', [])

    if "mod" not in user_groups:
        raise Exception({
            "statusCode": 403,
            "body": json.dumps("Access Denied: Insufficient permits")
        })

    try:
        body = json.loads(event['body'])
        if "id_user" not in body:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Missing id_user in body"})
            }
        id_user = body['id_user']
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
                delete_user_query = "DELETE FROM Users WHERE id_user = %s"
                rows_affected = cursor.execute(delete_user_query, (id_user,))
                connection.commit()
            except pymysql.MySQLError as e:
                connection.rollback()
                return {
                    "statusCode": 400,
                    "body": json.dumps({"message": str(e)})
                }
            if rows_affected == 0:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"message": "User not found"})
                }
            response = {
                "statusCode": 200,
                "body": json.dumps({"message": "User deleted successfully"})
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
