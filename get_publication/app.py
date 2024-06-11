import json

import pymysql

import boto3

from botocore.exceptions import ClientError


def get_secret():
    secret_name = 'sionpoKeys'
    region_name = 'us-east-2'

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)
    except ClientError as e:
        raise Exception(f"Error retrieving secret {secret_name}: {str(e)}")


def lambda_handler(event, context):
    secrets = get_secret()

    host = secrets['host']
    name = secrets['username']
    password = secrets['password']
    db_name = "SIONPO"

    connection = pymysql.connect(
        host=host,
        user=name,
        password=password,
        db=db_name,
        connect_timeout=5
    )

    try:
        with connection.cursor() as cursor:
            id_pokemon = event['queryStringParameters']['id_pokemon']
            cursor.execute("SELECT * FROM Pokemon WHERE id_pokemon = %s", (id_pokemon,))
            result = cursor.fetchone()

            if result:
                columns = [desc[0] for desc in cursor.description]
                result_dict = dict(zip(columns, result))
            else:
                result_dict = {}

        response = {
            "statusCode": 200,
            "body": json.dumps(result_dict, default=str)
        }

    except KeyError as e:
        response = {
            "statusCode": 400,
            "body": f"Missing key in request body: {str(e)}"
        }

    except pymysql.IntegrityError as e:
        response = {
            "statusCode": 422,
            "body": f"Database integrity error: {str(e)}"
        }

    except pymysql.OperationalError as e:
        response = {
            "statusCode": 503,
            "body": f"Database connection error: {str(e)}"
        }

    except pymysql.MySQLError as e:
        response = {
            "statusCode": 500,
            "body": str(e)
        }

    except Exception as e:
        response = {
            "statusCode": 403,
            "body": str(e)
        }

    finally:
        connection.close()

    return response
