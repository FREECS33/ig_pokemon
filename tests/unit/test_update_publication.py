import json
import unittest
from unittest.mock import patch, MagicMock

import pymysql
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from update_publication.app import get_secret, lambda_handler


class TestLambdaHandler(unittest.TestCase):

    @patch('update_publication.app.get_secret')
    @patch('pymysql.connect')
    def test_lambda_handler_success(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_cursor = mock_connection.cursor.return_value.__enter__.return_value
        mock_cursor.rowcount = 1

        event = {
            'body': json.dumps({
                'id_pokemon': 1,
                'updated_data': {
                    'name': 'Pikachu',
                    'type': 'Electric'
                }
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 200)
        data = json.loads(response['body'])
        self.assertEqual(data['message'], 'Pokemon updated successfully')

    @patch('update_publication.app.get_secret')
    def test_lambda_handler_missing_parameter(self, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        event = {
            'body': json.dumps({
                'id_pokemon': 1
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        data = json.loads(response['body'])
        self.assertEqual(data['message'], 'Missing id_pokemon or updated_data in request body')

    @patch('update_publication.app.get_secret')
    @patch('pymysql.connect')
    def test_lambda_handler_database_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'test_host',
            'username': 'test_user',
            'password': 'test_pass'
        }

        mock_connect.side_effect = pymysql.MySQLError(1045, 'Authentication error')

        event = {
            'body': json.dumps({
                'id_pokemon': 1,
                'updated_data': {
                    'name': 'Pikachu',
                    'type': 'Electric'
                }
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        data = json.loads(response['body'])
        self.assertIn('Error: (1045, \'Authentication error\')', data['message'])

    @patch('update_publication.app.get_secret')
    def test_lambda_handler_no_credentials_error(self, mock_get_secret):
        mock_get_secret.side_effect = NoCredentialsError()

        event = {
            'body': json.dumps({
                'id_pokemon': 1,
                'updated_data': {
                    'name': 'Pikachu',
                    'type': 'Electric'
                }
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        data = json.loads(response['body'])
        self.assertEqual(data['message'], 'Error: Unable to locate credentials')

    @patch('update_publication.app.get_secret')
    def test_lambda_handler_partial_credentials_error(self, mock_get_secret):
        mock_get_secret.side_effect = PartialCredentialsError(provider='aws', cred_var='secret_access_key')

        event = {
            'body': json.dumps({
                'id_pokemon': 1,
                'updated_data': {
                    'name': 'Pikachu',
                    'type': 'Electric'
                }
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        data = json.loads(response['body'])
        self.assertEqual(data['message'], 'Error: Partial credentials found in aws, missing: secret_access_key')

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

    # @patch('update_publication.app.get_secret')
    # @patch('pymysql.connect')
    # def test_lambda_handler_id_pokemon_not_found(self, mock_connect, mock_get_secret):
    #     mock_get_secret.return_value = {
    #         'host': 'test_host',
    #         'username': 'test_user',
    #         'password': 'test_pass'
    #     }
    #
    #     mock_connection = MagicMock()
    #     mock_connect.return_value = mock_connection
    #     mock_cursor = mock_connection.cursor.return_value.__enter__.return_value
    #
    #     mock_cursor.fetchone.return_value = None
    #
    #     event = {
    #         'body': json.dumps({
    #             'id_pokemon': 999,
    #             'updated_data': {
    #                 'name': 'Pikachu',
    #                 'type': 'Electric'
    #             }
    #         })
    #     }
    #     context = {}
    #
    #     response = lambda_handler(event, context)
    #
    #     self.assertEqual(response['statusCode'], 404)
    #     data = json.loads(response['body'])
    #     self.assertEqual(data['message'], 'Pokemon with id_pokemon 999 not found')


if __name__ == '__main__':
    unittest.main()
