import json
import pymysql
import boto3
from botocore.exceptions import ClientError


def get_secret():
    secret_name = 'sionpoKeys'
    region_name = 'us-east-2'

    session = boto3.session.Session()
    client = session.client(
        service_name='secretmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)
    except ClientError as e:
        raise Exception(f"Error retrieving secret {secret_name}: {str(e)}")


secrets = get_secret()

host = secrets['host']
name = secrets['username']
password = secrets['password']
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

        pokemon_name = body['pokemon_name']
        abilities = json.dumps(body['abilities'])
        types = json.dumps(body['types'])
        description = body['description']
        evolution_conditions = body['evolution_conditions']
        image = body['image']
        likes_count = body['likes_count']
        dislikes_count = body['dislikes_count']
        creation_update_date = body['creation_update_date']
        id_pokemon = body['id_pokemon']
        fk_id_user_creator = body['fk_id_user_creator']

        with connection.cursor() as cursor:
            sql = """
                    INSERT INTO Pokemon (
                        pokemon_name, abilities, types, description, 
                        evolution_conditions, image, likes_count, 
                        dislikes_count, creation_update_date, id_pokemon, fk_id_user_creator
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """
            cursor.execute(sql, (
                pokemon_name, abilities, types, description,
                evolution_conditions, image, likes_count,
                dislikes_count, creation_update_date, id_pokemon, fk_id_user_creator
            ))
            connection.commit()

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
