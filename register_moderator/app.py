import json
import pymysql
import boto3


def get_secret(secret_name):
    region_name = 'us-east-2'
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret = response['SecretString']
        return json.loads(secret)
    except Exception as e:
        raise Exception(f"Error retrieving secret {secret_name}: {str(e)}")


def lambda_handler(event, context):
    secrets = get_secret('sionpoKeys')
    connection = pymysql.connect(
        host=secrets['host'],
        user=secrets['username'],
        password=secrets['password'],
        db='SIONPO',
        connect_timeout=5
    )

    try:
        body = json.loads(event['body'])

        username = body['username']
        email = body['email']
        password = body['password']
        role = body['role']

        with connection.cursor() as cursor:
            sql = """
                    INSERT INTO Moderators (
                        username, email, password, role
                    ) VALUES (
                        %s, %s, %s, %s
                    )
                """
            cursor.execute(sql, (
                username, email, password, role
            ))
            connection.commit()

        response = {
            "statusCode": 200,
            "body": json.dumps({"message": "Moderator registered successfully"})
        }

    except pymysql.MySQLError as error:
        response = {
            "statusCode": 500,
            "body": str(error)
        }

    finally:
        connection.close()

    return response
