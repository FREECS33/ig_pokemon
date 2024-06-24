import unittest
from unittest.mock import patch, MagicMock
import json

import pymysql
from botocore.exceptions import ClientError
from pymysql import MySQLError
from post_badges import app

mock_body = {
    "body": json.dumps({
        "badge_name": "test_badge",
        "description": "test_description",
        "standard_to_get": "test_standard",
        "date_earned": "2021-01-01",
        "image": "test_image"
    })
}

class TestPostBadges(unittest.TestCase):

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

        response = app.lambda_handler(event, context)

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
            "body": json.dumps({
                "badge_name": "Example Badge"
            })
        }
        context = {}

        response = app.lambda_handler(event, context)

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
            "body": "invalid-json"
        }
        context = {}

        response = app.lambda_handler(event, context)

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

        response = app.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 503)
        response_body = json.loads(response['body'])
        self.assertIn("Can't connect to MySQL server on 'mock-host'", response_body["message"])

    @patch('post_badges.app.get_secret')
    def test_lambda_handler_get_secret_fail(self, mock_get_secret):
        mock_get_secret.side_effect = Exception("Test secret error")

        event = mock_body
        context = {}

        response = app.lambda_handler(event, context)

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

        response = app.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        response_body = json.loads(response['body'])
        self.assertIn("Insert failed", response_body["message"])


