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
            id_badge = event['queryStringParameters']['id_badge']


            update_users_sql = "UPDATE Users SET fk_id_badge = NULL WHERE fk_id_badge = %s"
            cursor.execute(update_users_sql, (id_badge,))
            connection.commit()


            delete_badge_sql = "DELETE FROM Badges WHERE id_badge = %s"
            cursor.execute(delete_badge_sql, (id_badge,))
            connection.commit()

        response = {
            "statusCode": 200,
            "body": json.dumps({"message": "Badge deleted successfully"})
        }
    except pymysql.MySQLError as error:
        response = {
            "statusCode": 500,
            "body": str(error)
        }
    finally:
        connection.close()
    return response
