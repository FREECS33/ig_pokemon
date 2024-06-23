import json
import unittest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from register_user.app import get_secret, lambda_handler


class TestLambdaHandler(unittest.TestCase):

    @patch('boto3.session.Session.client')
    def test_get_secret_success(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'USER_POOL_ID': 'mock_polId',
                'CLIENT_ID': 'mock_client_id',
                'CLIENT_SECRET': 'mock_client_secret'
            })
        }

        secret = get_secret()

        self.assertEqual(secret['USER_POOL_ID'], 'mock_polId')
        self.assertEqual(secret['CLIENT_ID'], 'mock_client_id')
        self.assertEqual(secret['CLIENT_SECRET'], 'mock_client_secret')

    @patch('register_user.app.get_secret')
    @patch('boto3.client')
    def test_lambda_handler_success(self, mock_boto_client, mock_get_secret):
        mock_get_secret.return_value = {
            'USER_POOL_ID': 'mock_polId',
            'CLIENT_ID': 'mock_client_id',
            'CLIENT_SECRET': 'mock_client_secret'
        }

        mock_cognito_client = MagicMock()
        mock_boto_client.return_value = mock_cognito_client
        mock_cognito_client.sign_up.return_value = {'UserSub': '1234'}

        event = {
            'body': json.dumps({
                'username': 'testuser',
                'password': 'TestPassword123!',
                'email': 'testuser@example.com',
                'picture': 'https://example.com/profile.jpg'
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 200)
        data = json.loads(response['body'])
        self.assertEqual(data['message'], 'User registration successful')
        self.assertIn('user_sub', data)

    @patch('register_user.app.get_secret')
    @patch('boto3.client')
    def test_lambda_handler_missing_parameter(self, mock_boto_client, mock_get_secret):
        mock_get_secret.return_value = {
            'USER_POOL_ID': 'mock_polId',
            'CLIENT_ID': 'mock_client_id',
            'CLIENT_SECRET': 'mock_client_secret'
        }

        event = {
            'body': json.dumps({
                'username': 'testuser',
                'password': 'TestPassword123!',
                'picture': 'https://example.com/profile.jpg'
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        data = json.loads(response['body'])
        self.assertIn('error', data)
        self.assertIn('Missing parameter', data['error'])

    @patch('register_user.app.get_secret')
    @patch('boto3.client')
    def test_lambda_handler_client_error(self, mock_boto_client, mock_get_secret):
        mock_get_secret.return_value = {
            'USER_POOL_ID': 'mock_polId',
            'CLIENT_ID': 'mock_client_id',
            'CLIENT_SECRET': 'mock_client_secret'
        }

        mock_cognito_client = MagicMock()
        mock_boto_client.return_value = mock_cognito_client
        mock_cognito_client.sign_up.side_effect = ClientError(
            {"Error": {"Code": "UsernameExistsException", "Message": "User already exists"}},
            "sign_up"
        )

        event = {
            'body': json.dumps({
                'username': 'testuser',
                'password': 'TestPassword123!',
                'email': 'testuser@example.com',
                'picture': 'https://example.com/profile.jpg'
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        data = json.loads(response['body'])
        self.assertIn('error', data)
        self.assertIn('UsernameExistsException', data['error'])

    @patch('register_user.app.get_secret')
    def test_lambda_handler_no_credentials_error(self, mock_get_secret):
        mock_get_secret.side_effect = NoCredentialsError()

        event = {
            'body': json.dumps({
                'username': 'testuser',
                'password': 'TestPassword123!',
                'email': 'testuser@example.com',
                'picture': 'https://example.com/profile.jpg'
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 401)
        data = json.loads(response['body'])
        self.assertIn('error', data)
        self.assertIn('AWS credentials not found', data['error'])

    @patch('register_user.app.get_secret')
    def test_lambda_handler_partial_credentials_error(self, mock_get_secret):
        mock_get_secret.side_effect = PartialCredentialsError(provider='aws', cred_var='secret_access_key')

        event = {
            'body': json.dumps({
                'username': 'testuser',
                'password': 'TestPassword123!',
                'email': 'testuser@example.com',
                'picture': 'https://example.com/profile.jpg'
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 401)
        data = json.loads(response['body'])
        self.assertIn('error', data)
        self.assertIn('Incomplete AWS credentials', data['error'])

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

    @patch('boto3.session.Session.client')
    def test_get_secret_invalid_request_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "InvalidRequestException"}},
            "get_secret_value"
        )

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 400)
        self.assertIn('Invalid request for secret cognitoKeys', context.exception.args[0]['body'])

    @patch('boto3.session.Session.client')
    def test_get_secret_invalid_parameter_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "InvalidParameterException"}},
            "get_secret_value"
        )

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 400)
        self.assertIn('Invalid parameter for secret cognitoKeys', context.exception.args[0]['body'])

    @patch('boto3.session.Session.client')
    def test_get_secret_access_denied_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException"}},
            "get_secret_value"
        )

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 403)
        self.assertIn('Access denied for secret cognitoKeys', context.exception.args[0]['body'])

    @patch('register_user.app.get_secret')
    @patch('boto3.client')
    def test_lambda_handler_general_exception(self, mock_get_secret, mock_boto_client):
        mock_get_secret.side_effect = Exception("General error")

        event = {
            'body': json.dumps({
                'username': 'testuser',
                'password': 'TestPassword123!',
                'email': 'testuser@example.com',
                'picture': 'https://example.com/profile.jpg'
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        data = json.loads(response['body'])
        self.assertIn('error', data)
        self.assertIn('Internal server error: General error', data['error'])

    @patch('boto3.session.Session.client')
    def test_get_secret_general_client_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "SomeOtherException"}},
            "get_secret_value"
        )

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 500)
        self.assertIn('Error retrieving secret cognitoKeys', context.exception.args[0]['body'])
