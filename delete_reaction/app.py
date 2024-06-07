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
