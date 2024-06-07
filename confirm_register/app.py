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
    confirmation_code = event['confirmation_code']

    client = boto3.client('cognito-idp')

    secret_hash = get_secret_hash(username, secret['CLIENT_ID'], secret['CLIENT_SECRET'])

    try:
        response = client.confirm_sign_up(
            ClientId=secret['CLIENT_ID'],
            Username=username,
            ConfirmationCode=confirmation_code,
            SecretHash=secret_hash,
        )
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'User account confirmed successfully'})
        }
    except ClientError as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': str(e)})
        }
