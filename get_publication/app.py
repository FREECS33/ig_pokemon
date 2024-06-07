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
    except pymysql.MySQLError as error:
        response = {
            "statusCode": 500,
            "body": str(error)
        }
    finally:
        connection.close()

    return response
