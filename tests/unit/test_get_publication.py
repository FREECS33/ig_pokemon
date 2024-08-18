import json
import unittest
from unittest.mock import patch, MagicMock

import pymysql
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

from get_publication.app import get_secret, lambda_handler

mock_event = {
    "headers": {
        #Actualizar token con uno que sea valido y no este expirado para ejecutar las pruebas unitarias (Access Token)
        "Authorization": "Bearer "
    },
    "queryStringParameters": {
        "id_pokemon": "1"
    }
}


class TestApp(unittest.TestCase):

    @patch('get_publication.app.boto3.session.Session.client')
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

    @patch("get_publication.app.get_secret")
    @patch("get_publication.app.pymysql.connect")
    def test_lambda_handler_success(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.fetchone.return_value = (1, 'Pikachu', 'Electric')
        mock_cursor.description = (('id_pokemon',), ('name',), ('type',))

        result = lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertTrue(body)
        self.assertEqual(body['id_pokemon'], 1)
        self.assertEqual(body['name'], 'Pikachu')
        self.assertEqual(body['type'], 'Electric')

    @patch("get_publication.app.get_secret")
    @patch("get_publication.app.pymysql.connect")
    def test_lambda_handler_no_data(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        result = lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertFalse(body)

    @patch("get_publication.app.get_secret")
    def test_lambda_handler_get_secret_fail(self, mock_get_secret):
        mock_get_secret.side_effect = ClientError(
            {'Error': {'Message': "Error.", 'Code': 'code'}, 'ResponseMetadata': {'RequestId': 'd576be',
                                                                                  'HTTPStatusCode': 400,
                                                                                  'HTTPHeaders': {
                                                                                      'x-amzn-requestid': 'd576be88-',
                                                                                      'content-type': 'application',
                                                                                      'content-length': '99',
                                                                                      'date': 'Sat, 15 ',
                                                                                      'connection': 'close'},
                                                                                  'RetryAttempts': 0},
             'Message': "Secrets Manager can't find the specified secret."},
            "GetSecretValue"
        )

        result = lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 403)
        body = json.loads(result["body"])
        self.assertIn("Error retrieving secret", body)

    @patch("get_publication.app.get_secret")
    @patch("get_publication.app.pymysql.connect")
    def test_lambda_handler_db_integrity_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connect.side_effect = pymysql.IntegrityError("Integrity error")

        result = lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 422)
        body = json.loads(result["body"])
        self.assertEqual(body, "Database integrity error: Integrity error")

    @patch("get_publication.app.get_secret")
    @patch("get_publication.app.pymysql.connect")
    def test_lambda_handler_db_operational_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connect.side_effect = pymysql.OperationalError("Database connection error")

        result = lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 503)
        body = json.loads(result["body"])
        self.assertEqual(body, "Database connection error: Database connection error")

    @patch("get_publication.app.get_secret")
    @patch("get_publication.app.pymysql.connect")
    def test_lambda_handler_generic_db_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connect.side_effect = pymysql.MySQLError("Generic database error")

        result = lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 500)
        body = json.loads(result["body"])
        self.assertEqual(body, "Database error: Generic database error")

    @patch('get_publication.app.boto3.session.Session.client')
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

    @patch('get_publication.app.boto3.session.Session.client')
    def test_get_secret_no_credentials_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = NoCredentialsError()

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 401)
        self.assertIn('AWS credentials not found', context.exception.args[0]['body'])

    @patch('get_publication.app.boto3.session.Session.client')
    def test_get_secret_partial_credentials_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = PartialCredentialsError(
            provider='aws', cred_var='AWS_SECRET_ACCESS_KEY'
        )

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 401)
        self.assertIn('Incomplete AWS credentials', context.exception.args[0]['body'])

    @patch('get_publication.app.boto3.session.Session.client')
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

    @patch('get_publication.app.boto3.session.Session.client')
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

    @patch('get_publication.app.boto3.session.Session.client')
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

    @patch('get_publication.app.boto3.session.Session.client')
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

    @patch('get_publication.app.boto3.session.Session.client')
    def test_get_secret_general_exception(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = Exception("Unknown error")

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 500)
        self.assertIn('Unknown error: Unknown error', context.exception.args[0]['body'])

    @patch("get_publication.app.get_secret")
    @patch("get_publication.app.pymysql.connect")
    def test_lambda_handler_key_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        event_with_missing_key = {
            "headers": {
                # Actualizar token con uno que sea valido y no este expirado
                "Authorization": "Bearer "
            },
            "queryStringParameters": {},
        }
        result = lambda_handler(event_with_missing_key, None)
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertIn("Missing key in request body", body)

    @patch("get_publication.app.get_secret")
    @patch("get_publication.app.pymysql.connect")
    def test_lambda_handler_integrity_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.execute.side_effect = pymysql.IntegrityError("Integrity error")

        result = lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 422)
        body = json.loads(result["body"])
        self.assertEqual(body, "Database integrity error: Integrity error")

    @patch("get_publication.app.get_secret")
    @patch("get_publication.app.pymysql.connect")
    def test_lambda_handler_operational_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.execute.side_effect = pymysql.OperationalError("Operational error")

        result = lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 503)
        body = json.loads(result["body"])
        self.assertEqual(body, "Database connection error: Operational error")

    @patch("get_publication.app.get_secret")
    @patch("get_publication.app.pymysql.connect")
    def test_lambda_handler_mysql_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.execute.side_effect = pymysql.MySQLError("Generic database error")

        result = lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 500)
        body = json.loads(result["body"])
        self.assertEqual(body, "Database error: Generic database error")

    @patch("get_publication.app.get_secret")
    @patch("get_publication.app.pymysql.connect")
    def test_lambda_handler_generic_exception(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.execute.side_effect = Exception("Unknown error")

        result = lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 403)
        body = json.loads(result["body"])
        self.assertEqual(body, "Unknown error")

    @patch('get_publication.app.get_secret')
    @patch('get_publication.app.pymysql.connect')
    def test_lambda_handler_missing_auth_header(self, mock_connect, mock_get_secret):
        event_missing = {
            "headers": {}
        }
        context = {}

        response = lambda_handler(event_missing, context)

        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Authorization header is missing", response["body"])

    @patch('get_publication.app.get_secret')
    @patch('get_publication.app.pymysql.connect')
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

    @patch('get_publication.app.get_secret')
    @patch('get_publication.app.pymysql.connect')
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

    @patch('get_publication.app.get_secret')
    @patch('get_publication.app.pymysql.connect')
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

    @patch('get_publication.app.get_secret')
    @patch('get_publication.app.pymysql.connect')
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
        print(response)

        self.assertEqual(response["statusCode"], 401)
        self.assertIn("Token has expired", response["body"])

    @patch('get_publication.app.get_secret')
    @patch('get_publication.app.pymysql.connect')
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
