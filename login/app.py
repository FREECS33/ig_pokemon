import json
import boto3
from botocore.exceptions import ClientError
import hmac
import hashlib
import base64


def get_secret():
    secret_name = 'cognitoKeys'
    region_name = 'us-east-2'

    session = boto3.session.Session()
    client = session.client(
        service_name='secretmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)
    except ClientError as e:
        raise Exception(f"Error retrieving secret {secret_name}: {str(e)}")


secrets = get_secret()
USER_POOL_ID = secrets['USER_POOL_ID']
CLIENT_ID = secrets['CLIENT_ID']
CLIENT_SECRET = secrets['CLIENT_SECRET']


def get_secret_hash(username, client_id, client_secret):
    message = username + client_id
    dig = hmac.new(client_secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()
    return base64.b64encode(dig).decode()


def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])

        username = body['username']
        password = body['password']

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
        return {
            'statusCode': 200,
            'body': json.dumps(
                {'message': 'User login successful', 'authentication_result': response['AuthenticationResult']})
        }
    except ClientError as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': str(e)})
        }
