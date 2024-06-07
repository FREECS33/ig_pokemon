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

        id_interaction = body['id_interaction']

        with connection.cursor() as cursor:
            sql = "DELETE FROM Interactions WHERE id_interaction = %s"
            cursor.execute(sql, (id_interaction,))
            connection.commit()

        response = {
            "statusCode": 200,
            "body": json.dumps({"message": "Interaction deleted successfully"})
        }

    except pymysql.MySQLError as error:
        response = {
            "statusCode": 500,
            "body": str(error)
        }

    finally:
        connection.close()

    return response
