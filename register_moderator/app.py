import json
import pymysql

from secrets_manager import get_secret

secret_name = "sionpoKeys"


def lambda_handler(event, context):
    secret = get_secret(secret_name)
    connection = pymysql.connect(
        host=secret['host'],
        user=secret['username'],
        password=secret['password'],
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
