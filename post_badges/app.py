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
        body = json.loads(event['body'])
        if 'badge_name' not in body or 'description' not in body or 'standard_to_get' not in body or 'date_earned' not in body or 'image' not in body:
            raise ValueError("Missing required fields")
    except ValueError as error:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": str(error)})
        }
    try:
        secrets = get_secret()
    except Exception as error:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": str(error)})
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
    except pymysql.MySQLError as error:
        return {
            "statusCode": 503,
            "body": json.dumps({"message": str(error)})
        }
    try:
        badge_name = body['badge_name']
        description = json.dumps(body['description'])
        standard_to_get = body['standard_to_get']
        date_earned = body['date_earned']
        image = body['image']

        with connection.cursor() as cursor:
            sql = """
                    INSERT INTO Badges (
                        badge_name, description, standard_to_get, date_earned, image
                    ) VALUES (
                        %s, %s, %s, %s, %s
                    )                    
                """
            cursor.execute(sql, (
                badge_name, description, standard_to_get, date_earned, image
            ))
            connection.commit()
    except pymysql.MySQLError as error:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": str(error)})
        }

        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM Badges")
            result = cursor.fetchall()

        response = {
            "statusCode": 200,
            "body": json.dumps(result, default=str)
        }

    except pymysql.MySQLError as error:

        response = {
            "statusCode": 500,
            "body": str(error)
        }

    finally:
        connection.close()

    return response
