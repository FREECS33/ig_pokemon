import json
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
import hmac
import hashlib
import base64


def get_secret():
    secret_name = 'cognitoKeys'
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

        secrets = get_secret()

        USER_POOL_ID = secrets['USER_POOL_ID']
        CLIENT_ID = secrets['CLIENT_ID']
        CLIENT_SECRET = secrets['CLIENT_SECRET']

        client = boto3.client('cognito-idp')

        secret_hash = get_secret_hash(username, CLIENT_ID, CLIENT_SECRET)

        response = client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password,
                'SECRET_HASH': secret_hash
            }
        )

        role = None
        user_groups = client.admin_list_groups_for_user(
            Username=username,
            UserPoolId=secrets['USER_POOL_ID']
        )
        if user_groups['Groups']:
            role = user_groups['Groups'][0]['GroupName']

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'User login successful',
                'id_token': response['AuthenticationResult']['IdToken'],
                'access_token': response['AuthenticationResult']['AccessToken'],
                'refresh_token': response['AuthenticationResult']['RefreshToken'],
                'role': role
            })
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
