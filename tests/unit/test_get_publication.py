import unittest
from unittest.mock import patch, MagicMock
import json
from get_publication import app  # Asegúrate de que el nombre del archivo y el módulo sean correctos
import pymysql
from botocore.exceptions import ClientError


class TestLambdaHandler(unittest.TestCase):

    def setUp(self):
        self.apigw_getone_event = {
            'queryStringParameters': {
                'id_pokemon': '1'
            }
        }

    @patch('get_publication.app.get_secret')
    @patch('get_publication.app.pymysql.connect')
    def test_lambda_handler_success(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'localhost',
            'username': 'user',
            'password': 'password'
        }

        mock_connection = mock_connect.return_value
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.fetchone.return_value = (1, 'Pikachu', 'Electric')
        mock_cursor.description = (('id_pokemon',), ('name',), ('type',))

        ret = app.lambda_handler(self.apigw_getone_event, "")

        self.assertEqual(ret["statusCode"], 200)
        data = json.loads(ret["body"])
        self.assertIsInstance(data, dict)
        self.assertIn("id_pokemon", data)

    @patch('get_publication.app.get_secret')
    @patch('get_publication.app.pymysql.connect')
    def test_lambda_handler_db_connection_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'localhost',
            'username': 'user',
            'password': 'password'
        }

        mock_connect.side_effect = pymysql.OperationalError("Connection error")

        ret = app.lambda_handler(self.apigw_getone_event, "")

        self.assertEqual(ret["statusCode"], 503)
        self.assertIn("Database connection error", ret["body"])

    @patch('get_publication.app.get_secret')
    @patch('get_publication.app.pymysql.connect')
    def test_lambda_handler_sql_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'localhost',
            'username': 'user',
            'password': 'password'
        }

        mock_connection = mock_connect.return_value
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.execute.side_effect = pymysql.MySQLError("SQL error")

        ret = app.lambda_handler(self.apigw_getone_event, "")

        self.assertEqual(ret["statusCode"], 500)
        self.assertIn("SQL error", ret["body"])

    @patch('get_publication.app.get_secret')
    def test_lambda_handler_client_error(self, mock_get_secret):
        mock_get_secret.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}}, "GetSecretValue"
        )

        ret = app.lambda_handler(self.apigw_getone_event, "")

        self.assertEqual(ret["statusCode"], 403)
        self.assertIn("Error retrieving secret", ret["body"])

    def test_lambda_handler_key_error(self):
        event = {'queryStringParameters': {}}

        ret = app.lambda_handler(event, "")

        self.assertEqual(ret["statusCode"], 400)
        self.assertIn("Missing key in request body", ret["body"])

