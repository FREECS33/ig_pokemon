import json
import unittest
from unittest.mock import patch, MagicMock

import pymysql
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

from post_publication.app import get_secret, lambda_handler

mock_body = {
    "body": json.dumps({
        "pokemon_name": "Pikachu",
        "abilities": ["Static", "Lightning Rod"],
        "types": ["Electric"],
        "description": "An electric Pokémon",
        "evolution_conditions": "Thunderstone",
        "image": "pikachu.png",
        "likes_count": 100,
        "dislikes_count": 10,
        "creation_update_date": "2024-06-05",
        "id_pokemon": 25,
        "fk_id_user_creator": 1
    })
}


class TestPostPublication(unittest.TestCase):

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

    @patch('post_publication.app.get_secret')
    @patch('post_publication.app.pymysql.connect')
    def test_lambda_handler_success(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'id': 1, 'pokemon_name': 'Pikachu'}]
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        event = mock_body

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 200)
        response_body = json.loads(response['body'])
        self.assertIsInstance(response_body, list)
        self.assertEqual(response_body[0]['pokemon_name'], 'Pikachu')

    @patch('post_publication.app.get_secret')
    def test_lambda_handler_missing_fields(self, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        event = {
            "body": json.dumps({
                "pokemon_name": "Pikachu"
            })
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 400)
        response_body = json.loads(response['body'])
        self.assertIsInstance(response_body, dict)
        self.assertIn('message', response_body)
        self.assertEqual(response_body['message'], 'Missing required field: abilities')

    @patch('post_publication.app.get_secret')
    def test_lambda_handler_invalid_json(self, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        event = {
            "body": "invalid json"
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 400)
        response_body = json.loads(response['body'])
        self.assertIsInstance(response_body, dict)
        self.assertIn('message', response_body)
        self.assertEqual(response_body['message'], 'Expecting value: line 1 column 1 (char 0)')

    @patch('post_publication.app.get_secret')
    def test_lambda_handler_negative_likes_count(self, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        event = {
            "body": json.dumps({
                "pokemon_name": "Pikachu",
                "abilities": ["Static", "Lightning Rod"],
                "types": ["Electric"],
                "description": "An electric Pokémon",
                "evolution_conditions": "Thunderstone",
                "image": "pikachu.png",
                "likes_count": -1,
                "dislikes_count": 10,
                "creation_update_date": "2024-06-05",
                "id_pokemon": 25,
                "fk_id_user_creator": 1
            })
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 422)
        response_body = json.loads(response['body'])
        self.assertIsInstance(response_body, dict)
        self.assertIn('message', response_body)
        self.assertEqual(response_body['message'], 'likes_count cannot be negative')

    @patch('post_publication.app.get_secret')
    def test_lambda_handler_negative_dislikes_count(self, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        event = {
            "body": json.dumps({
                "pokemon_name": "Pikachu",
                "abilities": ["Static", "Lightning Rod"],
                "types": ["Electric"],
                "description": "An electric Pokémon",
                "evolution_conditions": "Thunderstone",
                "image": "pikachu.png",
                "likes_count": 100,
                "dislikes_count": -1,
                "creation_update_date": "2024-06-05",
                "id_pokemon": 25,
                "fk_id_user_creator": 1
            })
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 422)
        response_body = json.loads(response['body'])
        self.assertIsInstance(response_body, dict)
        self.assertIn('message', response_body)
        self.assertEqual(response_body['message'], 'likes_count cannot be negative')

    @patch('post_publication.app.get_secret')
    def test_lambda_handler_get_secret_fail(self, mock_get_secret):
        mock_get_secret.side_effect = Exception("Test secret error")

        event = mock_body
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body["message"], "Test secret error")

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

    @patch("post_publication.app.get_secret")
    @patch("post_publication.app.pymysql.connect")
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

        result = lambda_handler(mock_body, None)
        self.assertEqual(result["statusCode"], 500)
        body = json.loads(result["body"])
        self.assertEqual(body, "Generic database error")

    @patch("post_publication.app.get_secret")
    @patch("post_publication.app.pymysql.connect")
    def test_lambda_handler_generic_db_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connect.side_effect = pymysql.MySQLError("Generic database error")

        result = lambda_handler(mock_body, None)
        self.assertEqual(result["statusCode"], 500)
        body = json.loads(result["body"])
        self.assertEqual(body, "Generic database error")

