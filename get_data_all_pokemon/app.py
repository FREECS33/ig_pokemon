import json
import pymysql
import boto3
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
    try:
        secrets = get_secret()

        body = json.loads(event['body'])

        if body.get('role') != 'user' or body.get('role') != 'mod':
            raise Exception({
                "statusCode": 401,
                "body": "Access denied to this resource"
            })

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
                connect_timeout=5
            )

            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT * FROM Pokemon")
                    result = cursor.fetchall()

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
