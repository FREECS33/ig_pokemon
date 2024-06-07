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
