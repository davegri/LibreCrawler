import os
from pymongo import MongoClient

addr = os.environ.get('MONGODB_PORT_27017_TCP_ADDR') or 'localhost'
port = int(os.environ.get('MONGODB_PORT_27017_TCP_PORT')) or 27017

client = MongoClient(addr, port)
DB = client['librestock_db']
BASE_DIR = os.path.dirname(__file__)
THUMBNAIL_DIR = os.path.join(BASE_DIR, 'thumbs/')
