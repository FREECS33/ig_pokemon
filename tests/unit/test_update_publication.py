import json
import unittest
from unittest.mock import patch, MagicMock

import pymysql
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from update_publication.app import get_secret, lambda_handler


class TestLambdaHandler(unittest.TestCase):

    @patch('update_publication.app.boto3.session.Session.client')
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

    @patch('update_publication.app.get_secret')
    @patch('update_publication.app.pymysql.connect')
    def test_lambda_handler_success(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_cursor = mock_connection.cursor.return_value.__enter__.return_value
        mock_cursor.rowcount = 1

        event = {
            "headers": {
                # Actualizar con un token valido y no expirado (Acces token)
                "Authorization": "Bearer "
            },
            'body': json.dumps({
                'id_pokemon': 1,
                'updated_data': {
                    'name': 'Pikachu',
                    'type': 'Electric'
                }
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 200)
        data = json.loads(response['body'])
        self.assertEqual(data['message'], 'Pokemon updated successfully')

    @patch('update_publication.app.get_secret')
    def test_lambda_handler_missing_parameter(self, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        event = {
            "headers": {
                # Actualizar con un token valido y no expirado (Acces token)
                "Authorization": "Bearer "
            },
            'body': json.dumps({
                'id_pokemon': 1
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        data = json.loads(response['body'])
        self.assertEqual(data['message'], 'Missing id_pokemon or updated_data in request body')

    @patch('update_publication.app.get_secret')
    @patch('update_publication.app.pymysql.connect')
    def test_lambda_handler_database_general_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connect.side_effect = pymysql.MySQLError(1045, 'Authentication error')

        event = {
            "headers": {
                # Actualizar con un token valido y no expirado (Acces token)
                "Authorization": "Bearer "
            },
            'body': json.dumps({
                'id_pokemon': 1,
                'updated_data': {
                    'name': 'Pikachu',
                    'type': 'Electric'
                }
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        data = json.loads(response['body'])
        self.assertIn('Error: (1045, \'Authentication error\')', data['message'])

    @patch('update_publication.app.boto3.session.Session.client')
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

    @patch('update_publication.app.boto3.session.Session.client')
    def test_get_secret_no_credentials_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = NoCredentialsError()

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 401)
        self.assertIn('AWS credentials not found', context.exception.args[0]['body'])

    @patch('update_publication.app.boto3.session.Session.client')
    def test_get_secret_partial_credentials_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = PartialCredentialsError(
            provider='aws', cred_var='AWS_SECRET_ACCESS_KEY'
        )

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 401)
        self.assertIn('Incomplete AWS credentials', context.exception.args[0]['body'])

    @patch('update_publication.app.boto3.session.Session.client')
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

    @patch('update_publication.app.boto3.session.Session.client')
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

    @patch('update_publication.app.boto3.session.Session.client')
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

    @patch('update_publication.app.boto3.session.Session.client')
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

    @patch('update_publication.app.boto3.session.Session.client')
    def test_get_secret_general_exception(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = Exception("Unknown error")

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 500)
        self.assertIn('Unknown error: Unknown error', context.exception.args[0]['body'])

    @patch('update_publication.app.get_secret')
    @patch('update_publication.app.pymysql.connect')
    def test_lambda_handler_missing_auth_header(self, mock_connect, mock_get_secret):
        event_missing = {
            "headers": {}
        }
        context = {}

        response = lambda_handler(event_missing, context)

        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Authorization header is missing", response["body"])

    @patch('update_publication.app.get_secret')
    @patch('update_publication.app.pymysql.connect')
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

    @patch('update_publication.app.get_secret')
    @patch('update_publication.app.pymysql.connect')
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

    @patch('update_publication.app.get_secret')
    @patch('update_publication.app.pymysql.connect')
    def test_lambda_handler_invalid_audience_token(self, mock_connect, mock_get_secret):
        event_invalid_audience = {
            "headers": {
                # Actualizar con un token valido, que no haya expirado (Id token)
                "Authorization": "Bearer "
            }
        }
        context = {}

        response = lambda_handler(event_invalid_audience, context)

        self.assertEqual(response["statusCode"], 401)
        self.assertIn("Invalid token: Invalid audience", response["body"])

    @patch('update_publication.app.get_secret')
    @patch('update_publication.app.pymysql.connect')
    def test_lambda_handler_expired_token(self, mock_connect, mock_get_secret):
        event_expired_token = {
            "headers": {
                # Actualizar con un token valido y que haya expirado (Access token)
                "Authorization": "Bearer "
            },
            "queryStringParameters": {
                "id_pokemon": "1"
            }
        }
        context = {}

        response = lambda_handler(event_expired_token, context)

        self.assertEqual(response["statusCode"], 401)
        self.assertIn("Token has expired", response["body"])

    @patch('update_publication.app.get_secret')
    @patch('update_publication.app.pymysql.connect')
    def test_lambda_handler_invalid_permits(self, mock_connect, mock_get_secret):
        event_token = {
            "headers": {
                # Actualizar con un token que no contenga los roles permitidos (Access Token)
                "Authorization": "Bearer "
            }
        }
        context = {}

        response = lambda_handler(event_token, context)

        self.assertEqual(response["statusCode"], 403)
        self.assertIn("Access Denied: Insufficient permits", response["body"])

    @patch('update_publication.app.get_secret')
    @patch('update_publication.app.pymysql.connect')
    def test_lambda_handler_authentication_db_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_connection.cursor.side_effect = pymysql.MySQLError(1045,
                                                                'Authentication error: Incorrect username or password')

        event = {
            "headers": {
                # Actualizar con un token valido y no expirado (Acces token)
                "Authorization": "Bearer "
            },
            'body': json.dumps({
                'id_pokemon': 1,
                'updated_data': {
                    'name': 'Pikachu',
                    'type': 'Electric'
                }
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 401)
        data = json.loads(response['body'])
        self.assertEqual(data['message'], 'Authentication error: Incorrect username or password')

    @patch('update_publication.app.get_secret')
    @patch('update_publication.app.pymysql.connect')
    def test_lambda_handler_database_not_found_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_connection.cursor.side_effect = pymysql.MySQLError(1049, 'Unknown database')

        event = {
            "headers": {
                # Actualizar con un token valido y no expirado (Acces token)
                "Authorization": "Bearer "
            },
            'body': json.dumps({
                'id_pokemon': 1,
                'updated_data': {
                    'name': 'Pikachu',
                    'type': 'Electric'
                }
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 404)
        data = json.loads(response['body'])
        self.assertEqual(data['message'], 'Database not found')

    @patch('update_publication.app.get_secret')
    @patch('update_publication.app.pymysql.connect')
    def test_lambda_handler_cannot_connect_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_connection.cursor.side_effect = pymysql.MySQLError(2003, 'Can\'t connect to MySQL server on')

        event = {
            "headers": {
                # Actualizar con un token valido y no expirado (Acces token)
                "Authorization": "Bearer "
            },
            'body': json.dumps({
                'id_pokemon': 1,
                'updated_data': {
                    'name': 'Pikachu',
                    'type': 'Electric'
                }
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 503)
        data = json.loads(response['body'])
        self.assertEqual(data['message'], 'Cannot connect to database server')

    @patch('update_publication.app.get_secret')
    @patch('update_publication.app.pymysql.connect')
    def test_lambda_handler_duplicate_entry_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_connection.cursor.side_effect = pymysql.MySQLError(1062, 'Duplicate entry')

        event = {
            "headers": {
                # Actualizar con un token valido y no expirado (Acces token)
                "Authorization": "Bearer "
            },
            'body': json.dumps({
                'id_pokemon': 1,
                'updated_data': {
                    'name': 'Pikachu',
                    'type': 'Electric'
                }
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 409)
        data = json.loads(response['body'])
        self.assertEqual(data['message'], 'Duplicate entry error')

    @patch('update_publication.app.get_secret')
    @patch('update_publication.app.pymysql.connect')
    def test_lambda_handler_data_too_long_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_connection.cursor.side_effect = pymysql.MySQLError(1406, 'Data too long for column')

        event = {
            "headers": {
                # Actualizar con un token valido y no expirado (Acces token)
                "Authorization": "Bearer "
            },
            'body': json.dumps({
                'id_pokemon': 1,
                'updated_data': {
                    'name': 'Pikachu',
                    'type': 'Electric'
                }
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 413)
        data = json.loads(response['body'])
        self.assertEqual(data['message'], 'Data too long for column')
