import json
import unittest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from delete_publication.app import get_secret, lambda_handler


class TestLambdaHandler(unittest.TestCase):

    @patch('delete_publication.app.get_secret')
    @patch('pymysql.connect')
    def test_lambda_handler_success(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'example-host',
            'username': 'example-user',
            'password': 'example-pass'
        }

        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.rowcount = 1

        event = {
            'queryStringParameters': {
                'id_pokemon': '1234'
            }
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 200)
        data = json.loads(response['body'])
        self.assertEqual(data['message'], 'Pokemon deleted successfully')

    @patch('delete_publication.app.get_secret')
    @patch('pymysql.connect')
    def test_lambda_handler_missing_parameter(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'example-host',
            'username': 'example-user',
            'password': 'example-pass'
        }

        event = {
            'queryStringParameters': {}
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        data = json.loads(response['body'])
        self.assertIn('message', data)
        self.assertIn('Missing id_pokemon in query parameters', data['message'])

    @patch('delete_publication.app.get_secret')
    @patch('pymysql.connect')
    def test_lambda_handler_client_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'example-host',
            'username': 'example-user',
            'password': 'example-pass'
        }

        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.rowcount = 0

        event = {
            'queryStringParameters': {
                'id_pokemon': '111231212'
            }
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 404)
        data = json.loads(response['body'])
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Pokemon not found')

    @patch('delete_publication.app.get_secret')
    def test_lambda_handler_no_credentials_error(self, mock_get_secret):
        mock_get_secret.side_effect = NoCredentialsError()

        event = {
            'queryStringParameters': {
                'id_pokemon': '1234'
            }
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 401)
        data = json.loads(response['body'])
        self.assertIn('message', data)
        self.assertIn('AWS credentials not found', data['message'])

    @patch('delete_publication.app.get_secret')
    def test_lambda_handler_partial_credentials_error(self, mock_get_secret):
        mock_get_secret.side_effect = PartialCredentialsError(provider='aws', cred_var='secret_access_key')

        event = {
            'queryStringParameters': {
                'id_pokemon': '1234'
            }
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 401)
        data = json.loads(response['body'])
        self.assertIn('message', data)
        self.assertIn('Incomplete AWS credentials', data['message'])

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
        self.assertIn('Secret sionpoKeys not found', context.exception.args[0]['body'])

    @patch('boto3.session.Session.client')
    def test_get_secret_no_credentials_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = NoCredentialsError()

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 401)
        self.assertIn('AWS credentials not found', context.exception.args[0]['body'])


if __name__ == '__main__':
    unittest.main()
