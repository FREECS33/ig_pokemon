import unittest
from unittest.mock import patch, MagicMock
import json

import pymysql
from botocore.exceptions import ClientError
from pymysql import MySQLError
from post_publication import app

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

    @patch('post_publication.app.get_secret')
    @patch('post_publication.app.pymysql.connect')
    def test_ñambda_handler_success(self, mock_connect, mock_get_secret):
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

        response = app.lambda_handler(event, None)

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

        response = app.lambda_handler(event, None)

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

        response = app.lambda_handler(event, None)

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

        response = app.lambda_handler(event, None)

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

        response = app.lambda_handler(event, None)

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

        response = app.lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body["message"], "Test secret error")

