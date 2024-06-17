from unittest.mock import patch, Mock, MagicMock
from botocore.exceptions import ClientError
from get_publication import app
import unittest
import json
import pymysql

mock_event = {
    "queryStringParameters": {
        "id_pokemon": "1"
    }
}

class TestApp(unittest.TestCase):

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

        result = app.lambda_handler(mock_event, None)
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

        result = app.lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertFalse(body)

    @patch("get_publication.app.get_secret")
    def test_lambda_handler_get_secret_fail(self, mock_get_secret):
        mock_get_secret.side_effect = ClientError(
            {'Error': {'Message': "Error.", 'Code': 'code'}, 'ResponseMetadata': {'RequestId': 'd576be',
            'HTTPStatusCode': 400, 'HTTPHeaders': {'x-amzn-requestid': 'd576be88-', 'content-type': 'application',
            'content-length': '99', 'date': 'Sat, 15 ', 'connection': 'close'}, 'RetryAttempts': 0},
            'Message': "Secrets Manager can't find the specified secret."},
            "GetSecretValue"
        )

        result = app.lambda_handler(mock_event, None)
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

        result = app.lambda_handler(mock_event, None)
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

        result = app.lambda_handler(mock_event, None)
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

        result = app.lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 500)
        body = json.loads(result["body"])
        self.assertEqual(body, "Database error: Generic database error")

# No if __name__ == '__main__': unittest.main()
