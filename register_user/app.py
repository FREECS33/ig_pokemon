import json
import boto3
from botocore.exceptions import ClientError
import hmac
import hashlib
import base64
from secrets_manager import get_secret

secret = get_secret('cognitoKeys')

USER_POOL_ID = secret['USER_POOL_ID']


def get_secret_hash(username, client_id, client_secret):
    message = username + client_id
    dig = hmac.new(client_secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()
    return base64.b64encode(dig).decode()


def lambda_handler(event, context):
    username = event['username']
    password = event['password']
    email = event['email']
    picture = event['picture']

    client = boto3.client('cognito-idp')

    secret_hash = get_secret_hash(username, secret['CLIENT_ID'], secret['CLIENT_SECRET'])

    try:
        response = client.sign_up(
            ClientId=secret['CLIENT_ID'],
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
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'User registration successful', 'user_sub': response['UserSub']})
        }
    except ClientError as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': str(e)})
        }
