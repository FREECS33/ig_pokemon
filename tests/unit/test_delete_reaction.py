import unittest
from unittest.mock import patch, MagicMock
import pymysql
from botocore.exceptions import ClientError
import json
from pymysql import MySQLError

from delete_reaction import app

mock_body = {
    "body": json.dumps({"id_interaction": 1})
}

class TestLambdaHandler(unittest.TestCase):

    @patch('delete_reaction.app.get_secret')
    @patch('delete_reaction.app.pymysql.connect')
    def test_lambda_handler_success(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.return_value = 1
        mock_connect.return_value = mock_connection

        event = mock_body
        context = {}

        response = app.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 200)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body["message"], "Interaction deleted successfully")

    @patch('delete_reaction.app.get_secret')
    def test_lambda_handler_missing_id_interaction(self, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        event = {
            "body": json.dumps({})
        }
        context = {}

        response = app.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body["error"], "Missing id_interaction in request body")

    @patch('delete_reaction.app.get_secret')
    def test_lambda_handler_invalid_json(self, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        event = {
            "body": "invalid-json"
        }
        context = {}

        response = app.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        response_body = json.loads(response['body'])
        self.assertIn("Expecting value", response_body["error"])

    @patch('delete_reaction.app.get_secret')
    @patch('delete_reaction.app.pymysql.connect')
    def test_lambda_handler_db_connection_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connect.side_effect = pymysql.OperationalError("(2003, 'Can\'t connect to MySQL server on \'mock-host\' (timed out)')")

        event = mock_body
        context = {}

        response = app.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 503)
        response_body = json.loads(response['body'])
        self.assertIn("Can't connect to MySQL server on 'mock-host'", response_body["error"])

    @patch('delete_reaction.app.get_secret')
    def test_lambda_handler_get_secret_fail(self, mock_get_secret):
        mock_get_secret.side_effect = Exception("Test secret error")

        event = mock_body
        context = {}

        response = app.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body["error"], "Test secret error")

    @patch('delete_reaction.app.get_secret')
    @patch('delete_reaction.app.pymysql.connect')
    def test_lambda_handler_delete_interaction_fail(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = pymysql.MySQLError("Delete failed")
        mock_connect.return_value = mock_connection

        event = mock_body
        context = {}

        response = app.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body["error"], "Error deleting interaction table")

    @patch('delete_reaction.app.get_secret')
    @patch('delete_reaction.app.pymysql.connect')
    def test_lambda_handler_interaction_not_found(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.return_value = 0  # Mocking interaction not found
        mock_connect.return_value = mock_connection

        event = mock_body
        context = {}

        response = app.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 404)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body["error"], "Interaction not found")

    @patch('delete_reaction.app.get_secret')
    @patch('delete_reaction.app.pymysql.connect')
    def test_lambda_handler_unexpected_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Unexpected error")  # Mocking unexpected error
        mock_connect.return_value = mock_connection

        event = mock_body
        context = {}

        response = app.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body["error"], "An unexpected error occurred")