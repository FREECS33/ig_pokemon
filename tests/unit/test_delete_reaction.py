import json
import unittest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from delete_reaction.app import get_secret, lambda_handler


class TestLambdaHandler(unittest.TestCase):

    @patch('delete_reaction.app.get_secret')
    @patch('pymysql.connect')
    def test_lambda_handler_success(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'example-host',
            'username': 'example-user',
            'password': 'example-pass'
        }

        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.rowcount = 1

        event = {
            'body': json.dumps({
                'id_interaction': '1234'
            })
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 200)
        data = json.loads(response['body'])
        self.assertEqual(data['message'], 'Interaction deleted successfully')

    @patch('delete_reaction.app.get_secret')
    @patch('pymysql.connect')
    def test_lambda_handler_missing_parameter(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'example-host',
            'username': 'example-user',
            'password': 'example-pass'
        }

        event = {
            'body': json.dumps({})
        }
        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        data = json.loads(response['body'])
        self.assertIn('message', data)
        self.assertIn('Missing id_interaction in request body', data['message'])

    @patch('boto3.session.Session.client')
    def test_get_secret_client_error(self, mock_boto_client):
        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Secrets Manager can\'t find the specified secret.'
            }
        }
        mock_boto_client.return_value.get_secret_value.side_effect = ClientError(
            error_response, 'get_secret_value'
        )

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 404)
        self.assertIn('Secret sionpoKeys not found', context.exception.args[0]['body'])

    @patch('boto3.session.Session.client')
    def test_get_secret_no_credentials_error(self, mock_boto_client):
        mock_boto_client.return_value.get_secret_value.side_effect = NoCredentialsError()

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 500)
        self.assertIn('AWS credentials not found', context.exception.args[0]['body'])

    @patch('boto3.session.Session.client')
    def test_get_secret_partial_credentials_error(self, mock_boto_client):
        mock_boto_client.return_value.get_secret_value.side_effect = PartialCredentialsError(provider='aws', cred_var='secret_access_key')

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 500)
        self.assertIn('Incomplete AWS credentials', context.exception.args[0]['body'])


if __name__ == '__main__':
    unittest.main()
