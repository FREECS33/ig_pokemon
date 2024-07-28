import json
import pymysql
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError


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
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            response = {
                "statusCode": 404,
                "body": f"Secret {secret_name} not found"
            }
        elif error_code == 'InvalidRequestException':
            response = {
                "statusCode": 400,
                "body": f"Invalid request for secret {secret_name}"
            }
        elif error_code == 'InvalidParameterException':
            response = {
                "statusCode": 400,
                "body": f"Invalid parameter for secret {secret_name}"
            }
        elif error_code == 'AccessDeniedException':
            response = {
                "statusCode": 403,
                "body": f"Access denied for secret {secret_name}"
            }
        else:
            response = {
                "statusCode": 500,
                "body": f"Error retrieving secret {secret_name}: {str(e)}"
            }
        raise Exception(response)
    except NoCredentialsError:
        raise Exception({
            "statusCode": 401,
            "body": "AWS credentials not found"
        })
    except PartialCredentialsError:
        raise Exception({
            "statusCode": 401,
            "body": "Incomplete AWS credentials"
        })
    except Exception as e:
        raise Exception({
            "statusCode": 500,
            "body": f"Unknown error: {str(e)}"
        })


def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        required_fields = ['badge_name', 'description', 'standard_to_get', 'date_earned', 'image']
        for field in required_fields:
            if field not in body:
                raise ValueError(f"Missing required field: {field}")

        badge_name = body['badge_name']
        description = json.dumps(body['description'])
        standard_to_get = body['standard_to_get']
        date_earned = body['date_earned']
        image = body['image']

    except (json.JSONDecodeError, ValueError) as error:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": str(error)})
        }

    try:
        secrets = get_secret()
    except Exception as error:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": str(error)})
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
    except pymysql.MySQLError as error:
        return {
            "statusCode": 503,
            "body": json.dumps({"message": str(error)})
        }

    try:
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

            cursor.execute("SELECT * FROM Badges")
            result = cursor.fetchall()

            response = {
                "statusCode": 200,
                "body": json.dumps({"badges": result})
            }

    except pymysql.MySQLError as error:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": str(error)})
        }
    finally:
        connection.close()

    return response
