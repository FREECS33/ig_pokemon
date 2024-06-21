import unittest
from unittest.mock import patch, MagicMock
import json
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from confirm_register.app import lambda_handler, get_secret


class TestLambdaHandler(unittest.TestCase):

    @patch('confirm_register.app.get_secret')
    @patch('boto3.client')
    def test_lambda_handler_success(self, mock_boto_client, mock_get_secret):
        mock_get_secret.return_value = {
            'USER_POOL_ID': 'mock_pool_id',
            'CLIENT_ID': 'mock_client_id',
            'CLIENT_SECRET': 'mock_client_secret'
        }

        mock_cognito_client = MagicMock()
        mock_boto_client.return_value = mock_cognito_client
        mock_cognito_client.confirm_sign_up.return_value = {
            'ResponseMetadata': {
                'HTTPStatusCode': 200
            }
        }

        event = {
            'body': json.dumps({
                'username': 'testuser',
                'confirmation_code': '123456'
            })
        }
        context = {}

        response = lambda_handler(event, context)
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(json.loads(response['body']), {'message': 'User account confirmed successfully'})

    @patch('confirm_register.app.get_secret')
    @patch('boto3.client')
    def test_lambda_handler_missing_parameter(self, mock_boto_client, mock_get_secret):
        mock_get_secret.return_value = {
            'USER_POOL_ID': 'mock_pool_id',
            'CLIENT_ID': 'mock_client_id',
            'CLIENT_SECRET': 'mock_client_secret'
        }

        event = {
            'body': json.dumps({
                'username': 'testuser'
                # Missing 'confirmation_code'
            })
        }
        context = {}

        response = lambda_handler(event, context)
        self.assertEqual(response['statusCode'], 400)
        self.assertIn('Missing parameter', json.loads(response['body'])['error'])

    @patch('confirm_register.app.get_secret')
    @patch('boto3.client')
    def test_lambda_handler_client_error(self, mock_boto_client, mock_get_secret):
        mock_get_secret.return_value = {
            'USER_POOL_ID': 'mock_pool_id',
            'CLIENT_ID': 'mock_client_id',
            'CLIENT_SECRET': 'mock_client_secret'
        }

        mock_cognito_client = MagicMock()
        mock_boto_client.return_value = mock_cognito_client
        mock_cognito_client.confirm_sign_up.side_effect = ClientError(
            {"Error": {"Code": "InvalidParameterException", "Message": "Invalid parameter"}}, "confirm_sign_up"
        )

        event = {
            'body': json.dumps({
                'username': 'testuser',
                'confirmation_code': '123456'
            })
        }
        context = {}

        response = lambda_handler(event, context)
        self.assertEqual(response['statusCode'], 400)
        self.assertIn('InvalidParameterException: Invalid parameter', json.loads(response['body'])['error'])

    @patch('boto3.session.Session.client')
    def test_get_secret_client_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}},
            "get_secret_value"
        )

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 404)
        self.assertIn('Secret cognitoKeys not found', context.exception.args[0]['body'])

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