import unittest
from unittest.mock import patch, MagicMock
import json
from botocore.exceptions import ClientError
import pymysql


from post_reaction import app

class TestLambda(unittest.TestCase):

    @patch("post_reaction.app.get_secret")
    @patch("post_reaction.app.pymysql.connect")
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

        mock_event = {
            "body": json.dumps({
                "Fk_id_user": "1",
                "Fk_id_pokemon": "25",
                "interaction_type": "like"
            })
        }

        result = app.lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertIn("Interacción añadida exitosamente", body["message"])

    @patch("post_reaction.app.get_secret")
    @patch("post_reaction.app.pymysql.connect")
    def test_lambda_handler_missing_fields(self, mock_connect, mock_get_secret):
        mock_event = {
            "body": json.dumps({
                "Fk_id_user": "1",
                "Fk_id_pokemon": "25"
            })
        }

        result = app.lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertIn("Missing required fields", body["message"])

    @patch("post_reaction.app.get_secret")
    @patch("post_reaction.app.pymysql.connect")
    def test_lambda_handler_invalid_interaction_type(self, mock_connect, mock_get_secret):
        mock_event = {
            "body": json.dumps({
                "Fk_id_user": "1",
                "Fk_id_pokemon": "25",
                "interaction_type": "invalid_type"
            })
        }

        result = app.lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertIn("Invalid interaction_type", body["message"])

    @patch("post_reaction.app.get_secret")
    def test_lambda_handler_invalid_json(self, mock_get_secret):
        mock_event = {
            "body": "invalid json"
        }

        result = app.lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 400)
        body = json.loads(result["body"])
        self.assertIn("Expecting value", body["message"])

    @patch("post_reaction.app.get_secret")
    def test_lambda_handler_get_secret_fail(self, mock_get_secret):
        mock_get_secret.side_effect = ClientError(
            {'Error': {'Message': "Secrets Manager can't find the specified secret.", 'Code': 'ResourceNotFoundException'},
             'ResponseMetadata': {'RequestId': 'd576be', 'HTTPStatusCode': 400, 'HTTPHeaders': {'x-amzn-requestid': 'd576be88-', 'content-type': 'application', 'content-length': '99', 'date': 'Sat, 15 ', 'connection': 'close'}, 'RetryAttempts': 0}},
            'GetSecretValue'
        )

        mock_event = {
            "body": json.dumps({
                "Fk_id_user": "1",
                "Fk_id_pokemon": "25",
                "interaction_type": "like"
            })
        }

        result = app.lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 500)
        body = json.loads(result["body"])
        self.assertIn("Error retrieving secret", body["message"])

    @patch("post_reaction.app.get_secret")
    @patch("post_reaction.app.pymysql.connect")
    def test_lambda_handler_db_connection_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connect.side_effect = pymysql.MySQLError("Connection error")

        mock_event = {
            "body": json.dumps({
                "Fk_id_user": "1",
                "Fk_id_pokemon": "25",
                "interaction_type": "like"
            })
        }

        result = app.lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 500)
        body = json.loads(result["body"])
        self.assertIn("Error connecting to the database", body["message"])

    @patch("post_reaction.app.get_secret")
    @patch("post_reaction.app.pymysql.connect")
    def test_lambda_handler_db_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.execute.side_effect = pymysql.MySQLError("Database error")

        mock_event = {
            "body": json.dumps({
                "Fk_id_user": "1",
                "Fk_id_pokemon": "25",
                "interaction_type": "like"
            })
        }

        result = app.lambda_handler(mock_event, None)
        self.assertEqual(result["statusCode"], 500)
        body = json.loads(result["body"])
        self.assertIn("Database error", body["message"])


