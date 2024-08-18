import unittest
from unittest.mock import patch, MagicMock
import json
import pymysql
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from get_data_all_pokemon.app import get_secret, lambda_handler

event = {
    "headers": {
        #Actualizar token con uno que sea valido y no este expirado para ejecutar las pruebas unitarias
        "Authorization": "Bearer eyJraWQiOiI1YW9nb3RzZk9PTFF1Mm1JNzJOVEV3VnRqZmJqUWFpUzE2d2pPT25kTkVzPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiI3MTBiYjVlMC01MGQxLTcwZTQtNTY3OS1hMzlkMWIxYjUyZWIiLCJjb2duaXRvOmdyb3VwcyI6WyJ1c2VyIl0sImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC51cy1lYXN0LTIuYW1hem9uYXdzLmNvbVwvdXMtZWFzdC0yX05EWFpPRzdEUSIsImNsaWVudF9pZCI6IjVzNWMxb2Zwa3EzMGdrYnQ2MXExaGRpY2ZkIiwib3JpZ2luX2p0aSI6IjNhZjc3ZGIyLTE2MmYtNDM4MS1hMWQxLTYzNGM3NjcyMzU5YSIsImV2ZW50X2lkIjoiZjE3NTU5ZjUtZWI1Ni00ZTBjLWFkYjctMDg4NjJkMmE0ZTEyIiwidG9rZW5fdXNlIjoiYWNjZXNzIiwic2NvcGUiOiJhd3MuY29nbml0by5zaWduaW4udXNlci5hZG1pbiIsImF1dGhfdGltZSI6MTcyMzk1MjA0OSwiZXhwIjoxNzIzOTU1NjQ5LCJpYXQiOjE3MjM5NTIwNDksImp0aSI6IjNmMzJkOTM5LTRmMWEtNDQxNC05OTAyLWNhZWY0MjJlYjFiOSIsInVzZXJuYW1lIjoic2VyaW8ifQ.RZ-J5SejgdrfyVgow1IJVXnHmS1mF4Z7qfOd4RjJeiIM6Pc8ThGax51DGBjSh3GQCrICW8LzksfAgXsZWinPSUFbbt8nBFWkMPjmk6tPs3z_JdzbKJ3XbOsV3uFU0dBEVi5D0-BxQ6xjg80hCWZQjJTen21V8LqWV_SzWoHpT-D7tcdRwaAIFhImn2sEZpvr5IPb2gBC5p1dDB7s_9gao0G4kvZ00xMHNCdNeSwcngHQny2b4G51_W-jYKV5W8oZNg785ss7DkRmFqXUwidAU_e8u_wI-j7uth6GQBywz4ceTOzXfCCot7S4wXI1DtWMb_bQtlVk-Y0FM5FUU_cmBg"
    },
    "body": json.dumps({
        "id_user": 1
    })
}


class TestLambdaHandler(unittest.TestCase):

    @patch('get_data_all_pokemon.app.boto3.session.Session.client')
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

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_success(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{'id': 1, 'name': 'Pikachu'}, {'id': 2, 'name': 'Bulbasaur'}]
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 200)
        response_body = json.loads(response['body'])
        self.assertIsInstance(response_body, list)

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_db_connection_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connect.side_effect = pymysql.MySQLError(
            2003, "(2003, 'Can\'t connect to MySQL server on \'mock-host\' (timed out)')")

        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 503)
        self.assertIn('Cannot connect to database server', response['body'])

    @patch('get_data_all_pokemon.app.get_secret')
    def test_lambda_handler_missing_secrets(self, mock_get_secret):
        mock_get_secret.return_value = {
            'username': 'mock-username',
            'password': 'mock-password'
        }

        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        self.assertIn('One or more secrets are missing', response['body'])

    @patch('get_data_all_pokemon.app.boto3.session.Session.client')
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

    @patch('get_data_all_pokemon.app.boto3.session.Session.client')
    def test_get_secret_no_credentials_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = NoCredentialsError()

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 401)
        self.assertIn('AWS credentials not found', context.exception.args[0]['body'])

    @patch('get_data_all_pokemon.app.boto3.session.Session.client')
    def test_get_secret_partial_credentials_error(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = PartialCredentialsError(
            provider='aws', cred_var='AWS_SECRET_ACCESS_KEY'
        )

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 401)
        self.assertIn('Incomplete AWS credentials', context.exception.args[0]['body'])

    @patch('get_data_all_pokemon.app.boto3.session.Session.client')
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

    @patch('get_data_all_pokemon.app.boto3.session.Session.client')
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

    @patch('get_data_all_pokemon.app.boto3.session.Session.client')
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

    @patch('get_data_all_pokemon.app.boto3.session.Session.client')
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

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_db_authentication_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connect.side_effect = pymysql.MySQLError(
            1045, "(1045, 'Access denied for user \'mock-username\'@\'mock-host\' (using password: YES)')")

        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 401)
        self.assertIn('Authentication error: Incorrect username or password', response['body'])

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_db_not_found_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connect.side_effect = pymysql.MySQLError(
            1049, "(1049, 'Unknown database \'SIONPO\'')")

        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 404)
        self.assertIn('Database not found', response['body'])

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_query_execution_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connection = MagicMock()
        mock_connection.cursor.side_effect = Exception("Some query error")
        mock_connect.return_value = mock_connection

        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        self.assertIn('Query execution error', response['body'])

    @patch('get_data_all_pokemon.app.get_secret')
    def test_lambda_handler_general_exception(self, mock_get_secret):
        mock_get_secret.side_effect = Exception("Some unknown error")

        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        self.assertIn('Error', response['body'])

    @patch('get_data_all_pokemon.app.boto3.session.Session.client')
    def test_get_secret_general_exception(self, mock_client):
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_secret_value.side_effect = Exception("Unknown error")

        with self.assertRaises(Exception) as context:
            get_secret()

        self.assertEqual(context.exception.args[0]['statusCode'], 500)
        self.assertIn('Unknown error: Unknown error', context.exception.args[0]['body'])

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_db_general_error(self, mock_connect, mock_get_secret):
        mock_get_secret.return_value = {
            'host': 'mock-host',
            'username': 'mock-username',
            'password': 'mock-password'
        }

        mock_connect.side_effect = pymysql.MySQLError(
            1234, "(1234, 'Some general MySQL error')")

        context = {}

        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        self.assertIn('Database connection error', response['body'])
        self.assertIn('Some general MySQL error', response['body'])

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_missing_auth_header(self, mock_connect, mock_get_secret):
        event_missing = {
            "headers": {}
        }
        context = {}

        response = lambda_handler(event_missing, context)

        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Authorization header is missing", response["body"])

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_invalid_auth_header(self, mock_connect, mock_get_secret):
        event_invalid = {
            "headers": {
                "Authorization": "Invalid token"
            }
        }
        context = {}

        response = lambda_handler(event_invalid, context)

        self.assertEqual(response['statusCode'], 400)
        self.assertIn('Authorization header must start with \'Bearer \'', response['body'])

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_invalid_token(self, mock_connect, mock_get_secret):
        event_invalid = {
            "headers": {
                "Authorization": "Bearer invalid_token"
            }
        }
        context = {}

        response = lambda_handler(event_invalid, context)

        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Invalid token", response["body"])

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_invalid_audience_token(self, mock_connect, mock_get_secret):
        event_invalid_audience = {
            "headers": {
                "Authorization": "Bearer eyJraWQiOiJcL1hQaHAzQ1UzYkNBQnp2dnM1ZTdLOG5hOGFtR2ZzSlRvZDhhYlYxc2dLUT0iLCJhbG"
                                 "ciOiJSUzI1NiJ9.eyJzdWIiOiI3MTBiYjVlMC01MGQxLTcwZTQtNTY3OS1hMzlkMWIxYjUyZWIiLCJjb2duaX"
                                 "RvOmdyb3VwcyI6WyJ1c2VyIl0sImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJpc3MiOiJodHRwczpcL1wvY29nbml"
                                 "0by1pZHAudXMtZWFzdC0yLmFtYXpvbmF3cy5jb21cL3VzLWVhc3QtMl9ORFhaT0c3RFEiLCJjb2duaXRvOnVz"
                                 "ZXJuYW1lIjoic2VyaW8iLCJwaWN0dXJlIjoiaHR0cDpcL1wvZXhhbXBsZS5jb21cL3BpY3R1cmUuanBnIiwib"
                                 "3JpZ2luX2p0aSI6IjNhZjc3ZGIyLTE2MmYtNDM4MS1hMWQxLTYzNGM3NjcyMzU5YSIsImF1ZCI6IjVzNWMxb2"
                                 "Zwa3EzMGdrYnQ2MXExaGRpY2ZkIiwiZXZlbnRfaWQiOiJmMTc1NTlmNS1lYjU2LTRlMGMtYWRiNy0wODg2MmQ"
                                 "yYTRlMTIiLCJ0b2tlbl91c2UiOiJpZCIsImF1dGhfdGltZSI6MTcyMzk1MjA0OSwiZXhwIjoxNzIzOTU1NjQ5"
                                 "LCJpYXQiOjE3MjM5NTIwNDksImp0aSI6ImNjNmIwZTRhLTBjMGItNDlmMi05MDU1LTIyYjI5NjdjNzkyNyIsI"
                                 "mVtYWlsIjoiYWxlamFuZHJvaWJhcnJhYnJpdG9AZ21haWwuY29tIn0.LOcF9zsOcGrx3pWX0aGOrJYffGo4Mh"
                                 "6yQSI0tE67c9GR8PUdcDJb7ROLBo3ghkF6b_9Ig9u8DS0jYIk7KuTpysx0EZey2bQTIKTTAfH0vvXT4otUsDe"
                                 "DnmzBKRM8at89ny3P9jnsdQz1JkGWXUs8ZpdHtUgUupRmGmO92tfjs7ndBYptk2_f-yPV8Cb8yO5n1pcKqyoP"
                                 "5SwJlS9YcHW3TqmVeJflWF-b2WRJqIROeXy5psPzfIMMZZtemk3jOVUYV0sB1DKU4FElEbCFtUBQRPznzX2h9"
                                 "H5T9t_7KDQ0uChRpYRTD26w92Bby8kzgJR6_Qfl_e-lrKh6wTAYtVBK3w"
            }
        }
        context = {}

        response = lambda_handler(event_invalid_audience, context)

        self.assertEqual(response["statusCode"], 401)
        self.assertIn("Invalid token: Invalid audience", response["body"])

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_expired_token(self, mock_connect, mock_get_secret):
        event_expired_token = {
            "headers": {
                "Authorization": "Bearer eyJraWQiOiI1YW9nb3RzZk9PTFF1Mm1JNzJOVEV3VnRqZmJqUWFpUzE2d2pPT25kTkVzPSIsIm"
                       "FsZyI6IlJTMjU2In0.eyJzdWIiOiI3MTBiYjVlMC01MGQxLTcwZTQtNTY3OS1hMzlkMWIxYjUyZWIiLCJ"
                       "jb2duaXRvOmdyb3VwcyI6WyJ1c2VyIl0sImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC51cy1lYXN0"
                       "LTIuYW1hem9uYXdzLmNvbVwvdXMtZWFzdC0yX05EWFpPRzdEUSIsImNsaWVudF9pZCI6IjVzNWMxb2Zwa"
                       "3EzMGdrYnQ2MXExaGRpY2ZkIiwib3JpZ2luX2p0aSI6Ijg2NGZmNjMwLTcyM2ItNDFkMS1hOGIwLTNmZD"
                       "hkYTZjYzA0NyIsImV2ZW50X2lkIjoiN2E0N2JjMGMtYzU1Ni00YzFmLWI4OGQtMzgzZWNlZmJiM2FmIiwi"
                       "dG9rZW5fdXNlIjoiYWNjZXNzIiwic2NvcGUiOiJhd3MuY29nbml0by5zaWduaW4udXNlci5hZG1pbiIsIm"
                       "F1dGhfdGltZSI6MTcyMzk0ODA5MCwiZXhwIjoxNzIzOTUxNjkwLCJpYXQiOjE3MjM5NDgwOTAsImp0aSI6"
                       "IjZhOGE5MzBlLTBiMjctNGJhOC05ZWQ3LTk2ZmY5Y2U2ZjhmMSIsInVzZXJuYW1lIjoic2VyaW8ifQ.Jk7"
                       "US_dawuJkljCr4zvwz1EJYWfGg6xT99bSgtFruyGJeO7ABEJ8t6a4PlxSD8lucWZQd5Xmae2k6DnmOzAd8"
                       "riHcF4d1Qo5Ede1Mn9XhCk-cameu3-hTUAlYel4YKHlSSyIaU-uimMzHpSZcB9XphGu81yXAVh6jNpOovM"
                       "FhQTTZH4AkXQiFTtKE4X7jFXQtUgEjAxteMQkCVSIPvTqbIAPSw_8lT4qTRzh_N4FkslPV2XHKxPQFP8fh"
                       "RmtrYPhZWIDcNLdrlZ-PFD2F_XNQ-Npt1t533IvrFo2a0z4Q2tbg-v9iHcvHXkcj3cSGq5KxeIKjeG8E_IZyF6IFQcCPg"
            }
        }
        context = {}

        response = lambda_handler(event_expired_token, context)

        self.assertEqual(response["statusCode"], 401)
        self.assertIn("Token has expired", response["body"])

    @patch('get_data_all_pokemon.app.get_secret')
    @patch('get_data_all_pokemon.app.pymysql.connect')
    def test_lambda_handler_invalid_permits(self, mock_connect, mock_get_secret):
        event_token = {
            "headers": {
                "Authorization": "Bearer eyJraWQiOiI1YW9nb3RzZk9PTFF1Mm1JNzJOVEV3VnRqZmJqUWFpUzE2d2pPT25kTkVzPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiJhMWFiNjVmMC05MDYxLTcwODQtODIxYS04MmUyYWI2OTIwMWYiLCJjb2duaXRvOmdyb3VwcyI6WyJhZG1pbSJdLCJpc3MiOiJodHRwczpcL1wvY29nbml0by1pZHAudXMtZWFzdC0yLmFtYXpvbmF3cy5jb21cL3VzLWVhc3QtMl9ORFhaT0c3RFEiLCJjbGllbnRfaWQiOiI1czVjMW9mcGtxMzBna2J0NjFxMWhkaWNmZCIsIm9yaWdpbl9qdGkiOiJmMjY3YmJkNC0xMDUzLTQ1ODgtYWUyOS0wYjFlNGYxNzkyNjUiLCJldmVudF9pZCI6IjA4ZjdiOWYyLTk3ZDUtNDcyNS1iNWNiLWRhNTU2YmJlMzIxNSIsInRva2VuX3VzZSI6ImFjY2VzcyIsInNjb3BlIjoiYXdzLmNvZ25pdG8uc2lnbmluLnVzZXIuYWRtaW4iLCJhdXRoX3RpbWUiOjE3MjM5NTI0MDIsImV4cCI6MTcyMzk1NjAwMiwiaWF0IjoxNzIzOTUyNDAyLCJqdGkiOiJkODY5ZTVlYy01MjNjLTQ5MjctOWFlOS04NjdlODQyM2JkOWIiLCJ1c2VybmFtZSI6InplbCJ9.t_YMvV-GX43_dulCzCNNzXoWttIAhVQvvSNpALg8bARUntAOjbGOkTDSjx0jvBVc0uzhAZbPlOi2zrkcl0mI0SuNnX5h7Hf1lt1JuxWYuutvdfhflc6ipYTAqX8asU6-1MYXLNHm-2uwD2yV57_kJsRqrdQWJiTGNYFuh4aeBsoZxjwMOfb4uUotyEZyDbl5qAbIJTTHdjEcdIqo1vQEG3Et3uHmQbEGcwweTuUiSz33IELY-47zwrja7gue5GZyOIf-s7IeK5YzIy2KiQiHCS-2afdB7G5K9ZxbzC2EKZu6u5iMmSVa9Tj7Bk5DKfmHNi2a4s9qUa0B9JHZBGeaWA"
            }
        }
        context = {}

        response = lambda_handler(event_token, context)

        self.assertEqual(response["statusCode"], 403)
        self.assertIn("Access Denied: Insufficient permits", response["body"])
