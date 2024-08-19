import json
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
import hmac
import hashlib
import base64
import pymysql


def get_secret(secret_name):
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
            raise Exception({
                "statusCode": 404,
                "body": f"Secret {secret_name} not found"
            })
        elif error_code == 'InvalidRequestException':
            raise Exception({
                "statusCode": 400,
                "body": f"Invalid request for secret {secret_name}"
            })
        elif error_code == 'InvalidParameterException':
            raise Exception({
                "statusCode": 400,
                "body": f"Invalid parameter for secret {secret_name}"
            })
        elif error_code == 'AccessDeniedException':
            raise Exception({
                "statusCode": 403,
                "body": f"Access denied for secret {secret_name}"
            })
        else:
            raise Exception({
                "statusCode": 500,
                "body": f"Error retrieving secret {secret_name}: {str(e)}"
            })
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


def get_secret_hash(username, client_id, client_secret):
    message = username + client_id
    dig = hmac.new(client_secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()
    return base64.b64encode(dig).decode()


def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        username = body['username']
        password = body['password']
        email = body['email']
        picture = body['picture']

        secrets_cognito = get_secret('cognitoKeys')
        secrets_db = get_secret('sionpoKeys')

        USER_POOL_ID = secrets_cognito.get('USER_POOL_ID')
        CLIENT_ID = secrets_cognito.get('CLIENT_ID')
        CLIENT_SECRET = secrets_cognito.get('CLIENT_SECRET')

        role = 'user'

        client = boto3.client('cognito-idp')

        secret_hash = get_secret_hash(username, CLIENT_ID, CLIENT_SECRET)

        response = client.sign_up(
            ClientId=CLIENT_ID,
            SecretHash=secret_hash,
            Username=username,
            Password=password,
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': email
                },
                {
                    'Name': 'picture',
                    'Value': picture
                }
            ],
        )

        client.admin_add_user_to_group(
            UserPoolId=USER_POOL_ID,
            Username=username,
            GroupName=role
        )

        host = secrets_db.get('host')
        name = secrets_db.get('username')
        password_db = secrets_db.get('password')
        db_name = 'SIONPO'

        if not all([host, name, password_db]):
            raise Exception({
                "statusCode": 500,
                "body": "One or more secrets are missing"
            })

        try:
            connection = pymysql.connect(
                host=host,
                user=name,
                password=password_db,
                db=db_name,
                connect_timeout=5
            )

            try:
                with connection.cursor() as cursor:
                    query = """
                        INSERT INTO Users (username, email, password, photo)
                        VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(query, (username, email, password, picture))
                    connection.commit()
            except Exception as e:
                return {
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
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS,PUT,DELETE',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            'body': json.dumps({'message': 'User registration successful', 'user_sub': response['UserSub']})
        }
    except KeyError as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Missing parameter: {str(e)}'})
        }
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'{error_code}: {error_message}'})
        }
    except NoCredentialsError:
        return {
            'statusCode': 401,
            'body': json.dumps({'error': 'AWS credentials not found'})
        }
    except PartialCredentialsError:
        return {
            'statusCode': 401,
            'body': json.dumps({'error': 'Incomplete AWS credentials'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }
