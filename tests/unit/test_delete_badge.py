import unittest
from unittest.mock import patch, MagicMock
import pymysql
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
import json

from pymysql import MySQLError

from delete_badges.app import get_secret, lambda_handler

mock_body = {
    "body": json.dumps({"id_badge": 1})
}


class TestDeleteBadge(unittest.TestCase):

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

    @patch("delete_badges.app.get_secret")
    @patch("delete_badges.app.pymysql.connect")
    def test_lambda_handler_success(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = [1, 1]
        mock_connect.return_value = mock_connection

        response = lambda_handler(mock_body, None)
        self.assertEqual(response["statusCode"], 200)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body["message"], "Badge deleted successfully")

    @patch("delete_badges.app.get_secret")
    def test_lambda_handler_missing_body(self, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock_host',
            'username': 'mock_username',
            'password': 'mock_password'
        }

        event = {
            'body': json.dumps({
                'some_other_key': 'some_value'
            })
        }

        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertEqual(body['message'], "Missing id_badge in request body")


    @patch("delete_badges.app.get_secret")
    def test_lambda_handler_invalid_body(self, mock_get_secret):
        event = {
            "body": "This is not a valid JSON"
        }
        response = lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 400)
        response_body = json.loads(response['body'])
        self.assertIn("Invalid JSON", response_body["message"])

    @patch("delete_badges.app.get_secret")
    def test_lambda_handler_secret_error(self, mock_get_secret):
        mock_get_secret.side_effect = Exception("Secret Error")
        response = lambda_handler(mock_body, None)
        self.assertEqual(response["statusCode"], 500)
        response_body = json.loads(response['body'])
        self.assertIn("Secret Error", response_body["error"])

    @patch("delete_badges.app.get_secret")
    @patch("delete_badges.app.pymysql.connect")
    def test_lambda_handler_connection_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }
        mock_connect.side_effect = MySQLError("Connection Error")
        response = lambda_handler(mock_body, None)
        self.assertEqual(response["statusCode"], 503)
        response_body = json.loads(response['body'])
        self.assertIn("error", response_body)

    @patch("delete_badges.app.get_secret")
    @patch("delete_badges.app.pymysql.connect")
    def test_lambda_handler_db_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Database Error")
        mock_connect.return_value = mock_connection

        response = lambda_handler(mock_body, None)
        self.assertEqual(response["statusCode"], 500)
        response_body = json.loads(response['body'])
        self.assertIn("error", response_body)

    @patch("delete_badges.app.get_secret")
    @patch("delete_badges.app.pymysql.connect")
    def test_lambda_handler_error_update(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = [pymysql.MySQLError("Update failed"), 1]
        mock_connect.return_value = mock_connection

        event = mock_body
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body["error"], "Error updating Users table")

    @patch("delete_badges.app.get_secret")
    @patch("delete_badges.app.pymysql.connect")
    def test_lambda_handler_error_delete(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = [1, pymysql.MySQLError("Delete failed")]
        mock_connect.return_value = mock_connection

        event = mock_body
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body["error"], "Error deleting badge")

    @patch("delete_badges.app.get_secret")
    @patch("delete_badges.app.pymysql.connect")
    def test_lambda_handler_error_not_found(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = [1, 0]
        mock_connect.return_value = mock_connection

        response = lambda_handler(mock_body, None)
        self.assertEqual(response["statusCode"], 404)
        response_body = json.loads(response['body'])
        self.assertIn("error", response_body)

    @patch('delete_badges.app.get_secret')
    @patch('delete_badges.app.pymysql.connect')
    def test_database_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock_host',
            'username': 'mock_username',
            'password': 'mock_password'
        }

        mock_connect.side_effect = pymysql.MySQLError("Database error")

        event = {
            'body': json.dumps({
                'id_badge': '123'
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 503)
        body = json.loads(response['body'])
        self.assertIn("Database connection error: Database error", body['error'])

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

    @patch('boto3.session.Session.client')
    def test_get_secret_general_exception(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = Exception("Unknown error")

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 500)
        self.assertIn('Unknown error: Unknown error', context.exception.args[0]['body'])
