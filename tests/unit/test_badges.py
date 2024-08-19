import json
import unittest
from unittest.mock import patch, MagicMock

import pymysql
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

from post_badges.app import get_secret, lambda_handler

mock_body = {
    "headers": {
        #Actualizar con un token valido y no expirado (Acces token)
        "Authorization": "Bearer "
    },
    "body": json.dumps({
        "badge_name": "test_badge",
        "description": "test_description",
        "standard_to_get": "test_standard",
        "date_earned": "2021-01-01",
        "image": "test_image"
    })
}


class TestPostBadges(unittest.TestCase):

    @patch('post_badges.app.boto3.session.Session.client')
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

    @patch('post_badges.app.get_secret')
    @patch('post_badges.app.pymysql.connect')
    def test_lambda_handler_success(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'id': 1, 'badge_name': 'Example Badge'}]  # Simulando retorno de fetchall()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        event = mock_body
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 200)
        response_body = json.loads(response['body'])
        self.assertIsInstance(response_body, dict)
        self.assertIn('badges', response_body)
        self.assertIsInstance(response_body['badges'], list)
        self.assertEqual(response_body['badges'][0]['badge_name'], 'Example Badge')

    @patch('post_badges.app.get_secret')
    def test_lambda_handler_missing_fields(self, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        event = {
            "headers": {
                # Actualizar con un token valido y no expirado (Acces token)
                "Authorization": "Bearer "
            },
            "body": json.dumps({
                "badge_name": "Example Badge"
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body["message"], "Missing required field: description")

    @patch('post_badges.app.get_secret')
    def test_lambda_handler_invalid_json(self, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        event = {
            "headers": {
                # Actualizar con un token valido y no expirado (Acces token)
                "Authorization": "Bearer "
            },
            "body": "invalid-json"
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        response_body = json.loads(response['body'])
        self.assertIn("Expecting value", response_body["message"])

    @patch('post_badges.app.get_secret')
    @patch('post_badges.app.pymysql.connect')
    def test_lambda_handler_db_connection_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connect.side_effect = pymysql.OperationalError(
            "(2003, 'Can\'t connect to MySQL server on \'mock-host\' (timed out)')")

        event = mock_body
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 503)
        response_body = json.loads(response['body'])
        self.assertIn("Can't connect to MySQL server on 'mock-host'", response_body["message"])

    @patch('post_badges.app.get_secret')
    def test_lambda_handler_get_secret_fail(self, mock_get_secret):
        mock_get_secret.side_effect = Exception("Test secret error")

        event = mock_body
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body["message"], "Test secret error")

    @patch('post_badges.app.get_secret')
    @patch('post_badges.app.pymysql.connect')
    def test_lambda_handler_insert_fail(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = pymysql.MySQLError("Insert failed")
        mock_connect.return_value = mock_connection

        event = mock_body
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        response_body = json.loads(response['body'])
        self.assertIn("Insert failed", response_body["message"])

    @patch('post_badges.app.boto3.session.Session.client')
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

    @patch('post_badges.app.boto3.session.Session.client')
    def test_get_secret_no_credentials_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = NoCredentialsError()

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 401)
        self.assertIn('AWS credentials not found', context.exception.args[0]['body'])

    @patch('post_badges.app.boto3.session.Session.client')
    def test_get_secret_partial_credentials_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = PartialCredentialsError(
            provider='aws', cred_var='AWS_SECRET_ACCESS_KEY'
        )

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 401)
        self.assertIn('Incomplete AWS credentials', context.exception.args[0]['body'])

    @patch('post_badges.app.boto3.session.Session.client')
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

    @patch('post_badges.app.boto3.session.Session.client')
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

    @patch('post_badges.app.boto3.session.Session.client')
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

    @patch('post_badges.app.boto3.session.Session.client')
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

    @patch('post_badges.app.boto3.session.Session.client')
    def test_get_secret_general_exception(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = Exception("Unknown error")

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 500)
        self.assertIn('Unknown error: Unknown error', context.exception.args[0]['body'])

    @patch('post_badges.app.get_secret')
    @patch('post_badges.app.pymysql.connect')
    def test_lambda_handler_missing_auth_header(self, mock_connect, mock_get_secret):
        event_missing = {
            "headers": {}
        }
        context = {}

        response = lambda_handler(event_missing, context)

        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Authorization header is missing", response["body"])

    @patch('post_badges.app.get_secret')
    @patch('post_badges.app.pymysql.connect')
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

    @patch('post_badges.app.get_secret')
    @patch('post_badges.app.pymysql.connect')
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

    @patch('post_badges.app.get_secret')
    @patch('post_badges.app.pymysql.connect')
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

    @patch('post_badges.app.get_secret')
    @patch('post_badges.app.pymysql.connect')
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

    @patch('post_badges.app.get_secret')
    @patch('post_badges.app.pymysql.connect')
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
