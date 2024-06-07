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
