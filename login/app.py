import json
import boto3
from botocore.exceptions import ClientError
import hmac
import hashlib
import base64

USER_POOL_ID = 'us-east-2_NDXZOG7DQ'
CLIENT_ID = '5s5c1ofpkq30gkbt61q1hdicfd'
CLIENT_SECRET = '1lokp6a2dcn0a27j7shp20qpog3qo9pnh6a9advg6sp73hgndkgd'


def get_secret_hash(username, client_id, client_secret):
    message = username + client_id
    dig = hmac.new(client_secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()
    return base64.b64encode(dig).decode()


def lambda_handler(event, context):
    username = event['username']
    password = event['password']

    client = boto3.client('cognito-idp')

    secret_hash = get_secret_hash(username, CLIENT_ID, CLIENT_SECRET)

    try:
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
            'body': json.dumps({'message': 'User login successful', 'authentication_result': response['AuthenticationResult']})
        }
    except ClientError as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': str(e)})
        }
