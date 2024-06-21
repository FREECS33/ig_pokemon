from unittest.mock import patch, Mock, MagicMock
from botocore.exceptions import ClientError
import unittest
import json
import pymysql

# Importa la lambda desde el archivo correcto
from delete_badges import app

mock_event = {
    "body": json.dumps({
        "id_badge": "123"
    })
}

class TestLambda(unittest.TestCase):

    @patch("delete_badges.app.get_secret")
    @patch("delete_badges.app.pymysql.connect")
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
        mock_cursor.execute.side_effect = [1, 1]  # Simulate 1 row affected for both queries

        result = app.lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertIn("Badge deleted successfully", body["message"])

        update_users_sql = "UPDATE Users SET fk_id_badge = NULL WHERE fk_id_badge = %s"
        delete_badge_sql = "DELETE FROM Badges WHERE id_badge = %s"
        mock_cursor.execute.assert_any_call(update_users_sql, ('123',))
        mock_cursor.execute.assert_any_call(delete_badge_sql, ('123',))
        mock_connection.commit.assert_called()
        mock_connection.close.assert_called()

    @patch("delete_badges.app.get_secret")
    @patch("delete_badges.app.pymysql.connect")
    def test_lambda_handler_badge_not_found(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = [1, 0]  # Simulate 1 row affected for update, 0 for delete

        result = app.lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 404)
        body = json.loads(result["body"])
        self.assertIn("Badge not found", body["error"])

    @patch("delete_badges.app.get_secret")
    @patch("delete_badges.app.pymysql.connect")
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
        self.assertIn("Database integrity error: Integrity error", body["error"])

    @patch("delete_badges.app.get_secret")
    @patch("delete_badges.app.pymysql.connect")
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
        self.assertIn("Database connection error: Database connection error", body["error"])

    @patch("delete_badges.app.get_secret")
    @patch("delete_badges.app.pymysql.connect")
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
        self.assertIn("Database error: Generic database error", body["error"])
    def test_lambda_handler_missing_id_badge(self):
        event = {
            "body": json.dumps({})
        }

        result = app.lambda_handler(event, None)
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertIn("Missing 'id_badge' in request body", body["error"])

    def test_lambda_handler_invalid_json(self):
        event = {
            "body": "invalid json"
        }

        result = app.lambda_handler(event, None)
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertIn("Expecting value", body["error"])

# No if __name__ == '__main__': unittest.main()
