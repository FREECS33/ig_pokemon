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
