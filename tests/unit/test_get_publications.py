import unittest
from unittest.mock import patch, MagicMock
import json
from get_data_all_pokemon import app

class TestLambdaHandler(unittest.TestCase):
    
    @patch('app.get_secret')
    @patch('app.pymysql.connect')
    def test_lambda_handler_success(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{'id': 1, 'name': 'Pikachu'}]
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        event = {}
        context = {}
        
        response = app(event, context)
        
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(json.loads(response['body']), [{'id': 1, 'name': 'Pikachu'}])
    
    @patch('app.get_secret')
    @patch('app.pymysql.connect')
    def test_lambda_handler_db_connection_error(self, mock_connect, mock_get_secret):
        # Mock secrets
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connect.side_effect = pymysql.MySQLError("(2003, 'Can\'t connect to MySQL server on \'mock-host\' (10061)')")

        event = {}
        context = {}

        response = app(event, context)

        self.assertEqual(response['statusCode'], 503)
        self.assertIn('Cannot connect to database server', response['body'])

    @patch('app.get_secret')
    def test_lambda_handler_missing_secrets(self, mock_get_secret):
        mock_get_secret.return_value = {
            'username': 'mock-username',
            'password': 'mock-password'
        }

        event = {}
        context = {}

        response = app(event, context)

        self.assertEqual(response['statusCode'], 500)
        self.assertIn('One or more secrets are missing', response['body'])
    
    @patch('app.boto3.session.Session.client')
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

    @patch('app.boto3.session.Session.client')
    def test_get_secret_no_credentials_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = NoCredentialsError()

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 401)
        self.assertIn('AWS credentials not found', context.exception.args[0]['body'])
