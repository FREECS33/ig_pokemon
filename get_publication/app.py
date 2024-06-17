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
    try:
        secrets = get_secret()
    except Exception as e:
        return {
            "statusCode": 403,
            "body": json.dumps(f"Error retrieving secret: {str(e)}")
        }

    host = secrets['host']
    name = secrets['username']
    password = secrets['password']
    db_name = "SIONPO"

    try:
        connection = pymysql.connect(
            host=host,
            user=name,
            password=password,
            db=db_name,
            connect_timeout=5
        )
    except pymysql.IntegrityError as e:
        return {
            "statusCode": 422,
            "body": json.dumps(f"Database integrity error: {str(e)}")
        }
    except pymysql.OperationalError as e:
        return {
            "statusCode": 503,
            "body": json.dumps(f"Database connection error: {str(e)}")
        }
    except pymysql.MySQLError as e:
        return {
            "statusCode": 500,
            "body": json.dumps(f"Database error: {str(e)}")
        }

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
            "body": json.dumps(f"Missing key in request body: {str(e)}")
        }

    except pymysql.IntegrityError as e:
        response = {
            "statusCode": 422,
            "body": json.dumps(f"Database integrity error: {str(e)}")
        }

    except pymysql.OperationalError as e:
        response = {
            "statusCode": 503,
            "body": json.dumps(f"Database connection error: {str(e)}")
        }

    except pymysql.MySQLError as e:
        response = {
            "statusCode": 500,
            "body": json.dumps(f"Database error: {str(e)}")
        }

    except Exception as e:
        response = {
            "statusCode": 403,
            "body": json.dumps(str(e))
        }

    finally:
        connection.close()

    return response
