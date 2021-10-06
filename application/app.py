from flask import Flask, request
import pymongo
from dotenv import load_dotenv
from datetime import timedelta

import os

load_dotenv()

#connect to database
# db_url = os.environ["MONGODB_URI"]
db_url = "mongodb+srv://rithik:capstoneproject@capstone1.86sce.mongodb.net/capstone1?retryWrites=true&w=majority"
client = pymongo.MongoClient(db_url)
db = client.capstone

app = Flask(__name__)

from application.api import *