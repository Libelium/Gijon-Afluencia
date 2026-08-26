from pymongo import MongoClient

from app.core.config.db_settings import MongoDbSettings


def get_mongo_db_connection():
    mongo_settings = MongoDbSettings()
    url = mongo_settings.CONNECTION_URI
    db = MongoClient(url)
    return db
