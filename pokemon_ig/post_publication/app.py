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
        # Deserializar el cuerpo del evento
        body = json.loads(event['body'])

        # Extraer los datos del cuerpo
        pokemon_name = body['pokemon_name']
        abilities = json.dumps(body['abilities'])  # Convertir a JSON antes de almacenar
        types = json.dumps(body['types'])  # Convertir a JSON antes de almacenar
        description = body['description']
        evolution_conditions = body['evolution_conditions']
        image = body['image']
        likes_count = body['likes_count']
        dislikes_count = body['dislikes_count']
        creation_update_date = body['creation_update_date']
        id_pokemon = body['id_pokemon']
        fk_id_user_creator = body['fk_id_user_creator']

        # Insertar el nuevo Pokémon
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

        # Consultar todos los Pokémon
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM Pokemon")
            result = cursor.fetchall()

        # Crear la respuesta
        response = {
            "statusCode": 200,
            "body": json.dumps(result, default=str)
        }

    except pymysql.MySQLError as error:
        # Si ocurre un error de MySQL, configurar la respuesta con código de estado 500
        response = {
            "statusCode": 500,
            "body": str(error)
        }

    finally:
        connection.close()

    return response
