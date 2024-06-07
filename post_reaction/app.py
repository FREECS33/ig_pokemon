import json
import pymysql

host = "sionpo.clouqoguo4hz.us-east-2.rds.amazonaws.com"
name = "admin"
password = "sionpo2024"
db_name = "SIONPO"

def lambda_handler(event, context):
    # Conecta a la base de datos
    connection = pymysql.connect(
        host=host,
        user=name,
        password=password,
        db=db_name,
        connect_timeout=5
    )

    try:
        # Parsear el cuerpo de la solicitud
        body = json.loads(event['body'])
        fk_id_user = body['Fk_id_user']
        fk_id_pokemon = body['Fk_id_pokemon']
        interaction_type = body['interaction_type']

        # Inserta la nueva interacción en la base de datos
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO Interactions (Fk_id_user, Fk_id_pokemon, interaction_type)
            VALUES (%s, %s, %s)
            """
            cursor.execute(sql, (fk_id_user, fk_id_pokemon, interaction_type))
            connection.commit()

        response = {
            "statusCode": 200,
            "body": json.dumps({"message": "Interacción añadida exitosamente"})
        }
    except pymysql.MySQLError as error:
        response = {
            "statusCode": 500,
            "body": str(error)
        }
    except json.JSONDecodeError as json_error:
        response = {
            "statusCode": 400,
            "body": str(json_error)
        }
    finally:
        connection.close()

    return response
