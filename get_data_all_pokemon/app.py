import json

import pymysql

host = "sionpo.clouqoguo4hz.us-east-2.rds.amazonaws.com"
name = "admin"
password = "sionpo2024"
db_name = "SIONPO"


def lambda_handler(event, context):
    connection = pymysql.connect(
        host=host,
        user=name,
        password=password,
        db=db_name,
        connect_timeout=5
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM Pokemon")
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