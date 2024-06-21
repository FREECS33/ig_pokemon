import json
import pymysql
import boto3
from botocore.exceptions import ClientError

def get_secret():
    secret_name = 'sionpoKeys'
    region_name = 'us-east-2'

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)
    except ClientError as e:
        raise Exception(f"Error retrieving secret: {e.response['Error']['Message']}")

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        if 'id_badge' not in body:
            raise ValueError("Missing 'id_badge' in request body")
        id_badge = body['id_badge']
    except (json.JSONDecodeError, ValueError) as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)})
        }

    try:
        secrets = get_secret()
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

    host = secrets['host']
    name = secrets['username']
    password = secrets['password']
    db_name = "SIONPO"

    try:
        connection = pymysql.connect(
            host=host,
            user=name,
            password=password,
            db=db_name,
            connect_timeout=5
        )
    except pymysql.OperationalError as e:
        return {
            "statusCode": 503,
            "body": json.dumps({"error": f"Database connection error: {str(e)}"})
        }
    except pymysql.IntegrityError as e:
        return {
            "statusCode": 422,
            "body": json.dumps({"error": f"Database integrity error: {str(e)}"})
        }
    except pymysql.MySQLError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Database error: {str(e)}"})
        }

    try:
        with connection.cursor() as cursor:
            update_users_sql = "UPDATE Users SET fk_id_badge = NULL WHERE fk_id_badge = %s"
            rows_affected_users = cursor.execute(update_users_sql, (id_badge,))
            connection.commit()

            delete_badge_sql = "DELETE FROM Badges WHERE id_badge = %s"
            rows_affected_badges = cursor.execute(delete_badge_sql, (id_badge,))
            connection.commit()

            if rows_affected_badges == 0:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"error": "Badge not found"})
                }

        response = {
            "statusCode": 200,
            "body": json.dumps({"message": "Badge deleted successfully"})
        }
    except pymysql.IntegrityError as e:
        response = {
            "statusCode": 422,
            "body": json.dumps({"error": f"Database integrity error: {str(e)}"})
        }
    except pymysql.MySQLError as e:
        response = {
            "statusCode": 500,
            "body": json.dumps({"error": f"Database error: {str(e)}"})
        }
    finally:
        connection.close()
    return response
