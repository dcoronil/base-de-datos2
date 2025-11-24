from pymongo import MongoClient
import os

# Leer variables del entorno (docker-compose las va a definir)
MONGO_HOST = os.getenv("MONGO_HOST", "mongo")
MONGO_PORT = int(os.getenv("MONGO_PORT", 27017))
MONGO_DB = os.getenv("MONGO_DB", "campus_connect")

# Cliente global
client = MongoClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}/")

# Selección de base de datos
db = client[MONGO_DB]

# Colecciones principales
users_col = db["users"]
projects_col = db["projects"]
messages_col = db["messages"]

def test_connection():
    try:
        client.admin.command("ping")
        return True
    except Exception as e:
        print("Error connecting to MongoDB:", e)
        return False
