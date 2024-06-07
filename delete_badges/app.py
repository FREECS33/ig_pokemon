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
