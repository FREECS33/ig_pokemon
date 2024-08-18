import unittest
from unittest.mock import patch, MagicMock
import json
import pymysql
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from get_data_all_pokemon.app import get_secret, lambda_handler

event = {
    "headers": {
        #Actualizar token con uno que sea valido y no este expirado para ejecutar las pruebas unitarias (Access Token)
        "Authorization": "Bearer "
    },
    "body": json.dumps({
        "id_user": 1
    })
}


class TestLambdaHandler(unittest.TestCase):

    @patch('get_data_all_pokemon.app.boto3.session.Session.client')
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

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_success(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{'id': 1, 'name': 'Pikachu'}, {'id': 2, 'name': 'Bulbasaur'}]
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 200)
        response_body = json.loads(response['body'])
        self.assertIsInstance(response_body, list)

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_db_connection_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connect.side_effect = pymysql.MySQLError(
            2003, "(2003, 'Can\'t connect to MySQL server on \'mock-host\' (timed out)')")

        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 503)
        self.assertIn('Cannot connect to database server', response['body'])

    @patch('get_data_all_pokemon.app.get_secret')
    def test_lambda_handler_missing_secrets(self, mock_get_secret):
        mock_get_secret.return_value = {
            'username': 'mock-username',
            'password': 'mock-password'
        }

        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        self.assertIn('One or more secrets are missing', response['body'])

    @patch('get_data_all_pokemon.app.boto3.session.Session.client')
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

    @patch('get_data_all_pokemon.app.boto3.session.Session.client')
    def test_get_secret_no_credentials_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = NoCredentialsError()

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 401)
        self.assertIn('AWS credentials not found', context.exception.args[0]['body'])

    @patch('get_data_all_pokemon.app.boto3.session.Session.client')
    def test_get_secret_partial_credentials_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = PartialCredentialsError(
            provider='aws', cred_var='AWS_SECRET_ACCESS_KEY'
        )

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 401)
        self.assertIn('Incomplete AWS credentials', context.exception.args[0]['body'])

    @patch('get_data_all_pokemon.app.boto3.session.Session.client')
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

    @patch('get_data_all_pokemon.app.boto3.session.Session.client')
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

    @patch('get_data_all_pokemon.app.boto3.session.Session.client')
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

    @patch('get_data_all_pokemon.app.boto3.session.Session.client')
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

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_db_authentication_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connect.side_effect = pymysql.MySQLError(
            1045, "(1045, 'Access denied for user \'mock-username\'@\'mock-host\' (using password: YES)')")

        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 401)
        self.assertIn('Authentication error: Incorrect username or password', response['body'])

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_db_not_found_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connect.side_effect = pymysql.MySQLError(
            1049, "(1049, 'Unknown database \'SIONPO\'')")

        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 404)
        self.assertIn('Database not found', response['body'])

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_query_execution_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connection = MagicMock()
        mock_connection.cursor.side_effect = Exception("Some query error")
        mock_connect.return_value = mock_connection

        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        self.assertIn('Query execution error', response['body'])

    @patch('get_data_all_pokemon.app.get_secret')
    def test_lambda_handler_general_exception(self, mock_get_secret):
        mock_get_secret.side_effect = Exception("Some unknown error")

        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        self.assertIn('Error', response['body'])

    @patch('get_data_all_pokemon.app.boto3.session.Session.client')
    def test_get_secret_general_exception(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = Exception("Unknown error")

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 500)
        self.assertIn('Unknown error: Unknown error', context.exception.args[0]['body'])

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_db_general_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connect.side_effect = pymysql.MySQLError(
            1234, "(1234, 'Some general MySQL error')")

        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        self.assertIn('Database connection error', response['body'])
        self.assertIn('Some general MySQL error', response['body'])

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_missing_auth_header(self, mock_connect, mock_get_secret):
        event_missing = {
            "headers": {}
        }
        context = {}

        response = lambda_handler(event_missing, context)

        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Authorization header is missing", response["body"])

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_invalid_auth_header(self, mock_connect, mock_get_secret):
        event_invalid = {
            "headers": {
                "Authorization": "Invalid token"
            }
        }
        context = {}

        response = lambda_handler(event_invalid, context)

        self.assertEqual(response['statusCode'], 400)
        self.assertIn('Authorization header must start with \'Bearer \'', response['body'])

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_invalid_token(self, mock_connect, mock_get_secret):
        event_invalid = {
            "headers": {
                "Authorization": "Bearer invalid_token"
            }
        }
        context = {}

        response = lambda_handler(event_invalid, context)

        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Invalid token", response["body"])

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_invalid_audience_token(self, mock_connect, mock_get_secret):
        event_invalid_audience = {
            "headers": {
                #Actualizar con un token valido, que no haya expirado (Id token)
                "Authorization": "Bearer "
            }
        }
        context = {}

        response = lambda_handler(event_invalid_audience, context)

        self.assertEqual(response["statusCode"], 401)
        self.assertIn("Invalid token: Invalid audience", response["body"])

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_expired_token(self, mock_connect, mock_get_secret):
        event_expired_token = {
            "headers": {
                #Actualizar con un token valido y que haya expirado (Access token)
                "Authorization": "Bearer "
            }
        }
        context = {}

        response = lambda_handler(event_expired_token, context)

        self.assertEqual(response["statusCode"], 401)
        self.assertIn("Token has expired", response["body"])

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_invalid_permits(self, mock_connect, mock_get_secret):
        event_token = {
            "headers": {
                #Actualizar con un token que no contenga los roles permitidos (Access Token)
                "Authorization": "Bearer "
            }
        }
        context = {}

        response = lambda_handler(event_token, context)

        self.assertEqual(response["statusCode"], 403)
        self.assertIn("Access Denied: Insufficient permits", response["body"])
