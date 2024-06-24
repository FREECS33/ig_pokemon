import unittest
from unittest.mock import patch, MagicMock

import pymysql
from botocore.exceptions import ClientError
import json

from pymysql import MySQLError

from delete_badges import app

mock_body = {
    "body": json.dumps({"id_badge": 1})
}

class TestDeleteBadge(unittest.TestCase):

    @patch("delete_badges.app.get_secret")
    @patch("delete_badges.app.pymysql.connect")
    def test_lambda_handler_success(self,mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = [1, 1]  # Mocking successful updates and deletes
        mock_connect.return_value = mock_connection

        response = app.lambda_handler(mock_body, None)
        self.assertEqual(response["statusCode"], 200)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body["message"], "Badge deleted successfully")

    @patch("delete_badges.app.get_secret")
    def test_lambda_handler_missing_body(self,mock_get_secret):
        event = {
            "body": json.dumps({})
        }
        response = app.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 400)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body["message"], "Missing id_badge in request body")

    @patch("delete_badges.app.get_secret")
    def test_lambda_handler_missing_body(self,mock_get_secret):
        event = {
            "body": "This is not a valid JSON"
        }
        response = app.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 400)
        response_body = json.loads(response['body'])
        self.assertIn("Invalid JSON", response_body["message"])

    @patch("delete_badges.app.get_secret")
    def test_lambda_hanlder_secret_error(self, mock_get_secret):
        mock_get_secret.side_effect = Exception("Secret Error")
        response = app.lambda_handler(mock_body, None)
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
        response = app.lambda_handler(mock_body, None)
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

        response = app.lambda_handler(mock_body, None)
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
        mock_cursor.execute.side_effect = [pymysql.MySQLError("Update failed"), 1]  # Mocking failed update
        mock_connect.return_value = mock_connection

        event = mock_body
        context = {}

        response = app.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body["error"], "Error updating Users table")

    @patch("delete_badges.app.get_secret")
    @patch("delete_badges.app.pymysql.connect")
    def test_lambda_handler_error_delete(self,mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = [1, pymysql.MySQLError("Delete failed")]  # Mocking failed delete
        mock_connect.return_value = mock_connection

        event = mock_body
        context = {}

        response = app.lambda_handler(event, context)

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

        response = app.lambda_handler(mock_body, None)
        self.assertEqual(response["statusCode"], 404)
        response_body = json.loads(response['body'])
        self.assertIn("error", response_body)