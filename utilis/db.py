from sqlalchemy import create_engine
import psycopg2

def get_connection():
    return create_engine(url="postgresql://{0}:{1}@{2}:{3}/{4}".format(
        "postgres", "Pgadmin2024#", "localhost", 5432, "chuo_routes_db"
    ))

print(get_connection())

def psycop_connection():
    return psycopg2.connect(database="chuo_routes_db", 
                            user="postgres", 
                            password="Pgadmin2024#", 
                            host="localhost",
                            port=5432)

print(psycop_connection())