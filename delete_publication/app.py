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
            raise Exception({
                "statusCode": 404,
                "body": json.dumps({"message": f"Secret {secret_name} not found"})
            })
        elif error_code == 'InvalidRequestException':
            raise Exception({
                "statusCode": 400,
                "body": json.dumps({"message": f"Invalid request for secret {secret_name}"})
            })
        elif error_code == 'InvalidParameterException':
            raise Exception({
                "statusCode": 400,
                "body": json.dumps({"message": f"Invalid parameter for secret {secret_name}"})
            })
        elif error_code == 'AccessDeniedException':
            raise Exception({
                "statusCode": 403,
                "body": json.dumps({"message": f"Access denied for secret {secret_name}"})
            })
        else:
            raise Exception({
                "statusCode": 500,
                "body": json.dumps({"message": f"Error retrieving secret {secret_name}: {str(e)}"})
            })
    except NoCredentialsError:
        raise Exception({
            "statusCode": 401,
            "body": json.dumps({"message": "AWS credentials not found"})
        })
    except PartialCredentialsError:
        raise Exception({
            "statusCode": 401,
            "body": json.dumps({"message": "Incomplete AWS credentials"})
        })
    except Exception as e:
        raise Exception({
            "statusCode": 500,
            "body": json.dumps({"message": f"Unknown error: {str(e)}"})
        })


def lambda_handler(event, context):
    try:
        secrets = get_secret()

        host = secrets['host']
        name = secrets['username']
        password = secrets['password']
        db_name = "SIONPO"

        connection = pymysql.connect(
            host=host,
            user=name,
            password=password,
            db=db_name,
            connect_timeout=5
        )

        try:
            with connection.cursor() as cursor:
                id_pokemon = event.get('queryStringParameters', {}).get('id_pokemon')
                if not id_pokemon:
                    response = {
                        "statusCode": 400,
                        "body": json.dumps({"message": "Missing id_pokemon in query parameters"})
                    }
                    return response

                cursor.execute("DELETE FROM Pokemon WHERE id_pokemon = %s", (id_pokemon,))
                connection.commit()

                if cursor.rowcount == 0:
                    response = {
                        "statusCode": 404,
                        "body": json.dumps({"message": "Pokemon not found"})
                    }
                else:
                    response = {
                        "statusCode": 200,
                        "body": json.dumps({"message": "Pokemon deleted successfully"})
                    }
                return response
        finally:
            connection.close()

    except NoCredentialsError:
        return {
            "statusCode": 401,
            "body": json.dumps({"message": "AWS credentials not found"})
        }
    except PartialCredentialsError:
        return {
            "statusCode": 401,
            "body": json.dumps({"message": "Incomplete AWS credentials"})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": str(e)})
        }
