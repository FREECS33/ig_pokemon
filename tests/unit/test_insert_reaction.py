import unittest
from unittest.mock import patch, MagicMock
import json
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
import pymysql
from post_reaction.app import get_secret, lambda_handler


class TestLambdaHandler(unittest.TestCase):

    @patch('boto3.session.Session.client')
    def test_get_secret_success(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'host': 'mock-host',
                'username': 'mock-username',
                'password': 'mock-password'
            })
        }

        secret = get_secret()

        self.assertEqual(secret['host'], 'mock-host')
        self.assertEqual(secret['username'], 'mock-username')
        self.assertEqual(secret['password'], 'mock-password')

    @patch('post_reaction.app.get_secret')
    @patch('pymysql.connect')
    def test_lambda_handler_success(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.return_value = None
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        event = {
            "body": json.dumps({
                "Fk_id_user": 1,
                "Fk_id_pokemon": 25,
                "interaction_type": "like"
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 200)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body['message'], 'Interacción añadida exitosamente')

    @patch('post_reaction.app.get_secret')
    @patch('pymysql.connect')
    def test_lambda_handler_missing_fields(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        event = {
            "body": json.dumps({
                "Fk_id_user": 1,
                "Fk_id_pokemon": 25
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        response_body = json.loads(response['body'])
        self.assertIn('Missing required fields', response_body['message'])

    @patch('post_reaction.app.get_secret')
    @patch('pymysql.connect')
    def test_lambda_handler_invalid_interaction_type(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        event = {
            "body": json.dumps({
                "Fk_id_user": 1,
                "Fk_id_pokemon": 25,
                "interaction_type": "invalid_type"
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        response_body = json.loads(response['body'])
        self.assertIn('Invalid interaction_type', response_body['message'])

    @patch('post_reaction.app.get_secret')
    @patch('pymysql.connect')
    def test_lambda_handler_db_connection_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connect.side_effect = pymysql.MySQLError(
            2003, "(2003, 'Can\'t connect to MySQL server on \'mock-host\' (timed out)')")

        event = {
            "body": json.dumps({
                "Fk_id_user": 1,
                "Fk_id_pokemon": 25,
                "interaction_type": "like"
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 503)
        self.assertIn('Cannot connect to database server', response['body'])

    @patch('post_reaction.app.get_secret')
    def test_lambda_handler_missing_secrets(self, mock_get_secret):
        mock_get_secret.return_value = {
            'username': 'mock-username',
            'password': 'mock-password'
        }

        event = {
            "body": json.dumps({
                "Fk_id_user": 1,
                "Fk_id_pokemon": 25,
                "interaction_type": "like"
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        self.assertIn('One or more secrets are missing', response['body'])

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
    def test_get_secret_invalid_request_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "InvalidRequestException"}},
            "get_secret_value"
        )

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 400)
        self.assertIn('Invalid request for secret sionpoKeys', context.exception.args[0]['body'])

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
        self.assertIn('Invalid parameter for secret sionpoKeys', context.exception.args[0]['body'])

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
        self.assertIn('Access denied for secret sionpoKeys', context.exception.args[0]['body'])

    @patch('boto3.session.Session.client')
    def test_get_secret_unknown_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "SomeUnknownException"}},
            "get_secret_value"
        )

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 500)
        self.assertIn('Error retrieving secret sionpoKeys', context.exception.args[0]['body'])

    @patch('post_reaction.app.get_secret')
    @patch('pymysql.connect')
    def test_lambda_handler_db_authentication_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connect.side_effect = pymysql.MySQLError(
            1045, "(1045, 'Access denied for user \'mock-username\'@\'mock-host\' (using password: YES)')")

        event = {
            "body": json.dumps({
                "Fk_id_user": 1,
                "Fk_id_pokemon": 25,
                "interaction_type": "like"
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 401)
        self.assertIn('Authentication error: Incorrect username or password', response['body'])

    @patch('boto3.session.Session.client')
    def test_get_secret_general_exception(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = Exception("Unknown error")

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 500)
        self.assertIn('Unknown error: Unknown error', context.exception.args[0]['body'])

    @patch('post_reaction.app.get_secret')
    @patch('pymysql.connect')
    def test_lambda_handler_query_execution_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connection = MagicMock()
        mock_connection.cursor.side_effect = Exception("Some query error")
        mock_connect.return_value = mock_connection

        event = {}
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        self.assertIn('Query execution error', response['body'])

    @patch('post_reaction.app.get_secret')
    @patch('pymysql.connect')
    def test_lambda_handler_db_not_found_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connect.side_effect = pymysql.MySQLError(
            1049, "(1049, 'Unknown database \'SIONPO\'')")

        event = {}
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 404)
        self.assertIn('Database not found', response['body'])

    @patch('post_reaction.app.get_secret')
    @patch('pymysql.connect')
    def test_lambda_handler_db_general_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connect.side_effect = pymysql.MySQLError(
            1234, "(1234, 'Some general MySQL error')")

        event = {}
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        self.assertIn('Database connection error', response['body'])
        self.assertIn('Some general MySQL error', response['body'])

    @patch('post_reaction.app.get_secret')
    def test_lambda_handler_general_exception(self, mock_get_secret):
        mock_get_secret.side_effect = Exception("Some unknown error")

        event = {}
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        self.assertIn('Error', response['body'])
