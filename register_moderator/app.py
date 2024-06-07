import json
import pymysql

host = "sionpo.clouqoguo4hz.us-east-2.rds.amazonaws.com"
name = "admin"
contra = "sionpo2024"
db_name = "SIONPO"


def lambda_handler(event, context):
    connection = pymysql.connect(
        host=host,
        user=name,
        password=contra,
        db=db_name,
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
