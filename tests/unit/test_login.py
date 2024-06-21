import unittest
from unittest.mock import patch, MagicMock
import json

from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from login.app import lambda_handler, get_secret


class TestLambdaHandler(unittest.TestCase):

    @patch('login.app.get_secret')
    @patch('boto3.client')
    def test_lambda_handler_success(self, mock_boto_client, mock_get_secret):
        mock_get_secret.return_value = {
            'USER_POOL_ID': 'mock_pool_id',
            'CLIENT_ID': 'mock_client_id',
            'CLIENT_SECRET': 'mock_client_secret'
        }

        mock_cognito_client = MagicMock()
        mock_boto_client.return_value = mock_cognito_client
        mock_cognito_client.initiate_auth.return_value = {
            'AuthenticationResult': {
                'AccessToken': 'mock_access_token',
                'ExpiresIn': 3600,
                'TokenType': 'Bearer'
            }
        }

        event = {
            'body': json.dumps({
                'username': 'testuser',
                'password': 'testpassword'
            })
        }
        context = {}

        response = lambda_handler(event, context)
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['message'], 'User login successful')
        self.assertIn('authentication_result', body)

    @patch('login.app.get_secret')
    @patch('boto3.client')
    def test_lambda_handler_client_error(self, mock_boto_client, mock_get_secret):
        mock_get_secret.return_value = {
            'USER_POOL_ID': 'mock_pool_id',
            'CLIENT_ID': 'mock_client_id',
            'CLIENT_SECRET': 'mock_client_secret'
        }

        mock_cognito_client = MagicMock()
        mock_boto_client.return_value = mock_cognito_client
        mock_cognito_client.initiate_auth.side_effect = ClientError(
            {"Error": {"Code": "NotAuthorizedException", "Message": "Incorrect username or password"}}, "initiate_auth"
        )

        event = {
            'body': json.dumps({
                'username': 'testuser',
                'password': 'wrongpassword'
            })
        }
        context = {}

        response = lambda_handler(event, context)
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertIn('NotAuthorizedException', body['error'])

    @patch('boto3.session.Session.client')
    def test_get_secret_no_credentials_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = NoCredentialsError()

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 401)
        self.assertIn('AWS credentials not found', context.exception.args[0]['body'])

    @patch('boto3.session.Session.client')
    def test_get_secret_partial_credentials_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = PartialCredentialsError(
            provider='aws', cred_var='AWS_SECRET_ACCESS_KEY'
        )

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 401)
        self.assertIn('Incomplete AWS credentials', context.exception.args[0]['body'])

    @patch('boto3.session.Session.client')
    def test_get_secret_unknown_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = Exception("Unknown error")

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 500)
        self.assertIn('Unknown error', context.exception.args[0]['body'])
