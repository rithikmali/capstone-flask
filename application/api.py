from application.app import app,db
from flask import Flask, request
from werkzeug.utils import secure_filename
import json
import re
import random
from collections import defaultdict
from bson import json_util
import bson
from bson.binary import Binary
import collections
from bson.codec_options import CodecOptions

@app.route("/api")
def home():
    return {"Status": "Success"}, 200 

# Write your API endpoints here

@app.route('/api/upload',methods=['POST'])
def check_form():
    chapter = request.values.get('chapter')
    quizname = request.values.get('quizname')
    minutes = request.values.get('minutes')
    seconds = request.values.get('seconds')
    filename = "no pdf"
    try:
        pdf = request.files['file']
        filename = secure_filename(pdf.filename)
    except:
        print('no pdf')
    
    quiz_card_db_val = {'chapter': chapter,'quizname': quizname,
                'filename': filename, 'time': {'minutes': int(minutes), 'seconds': int(seconds)}}
    mycol = db['pdfs']
    x = mycol.insert_one(quiz_card_db_val)
    print('inserted into pdf db')
    return 'received form',200

def parse_json(data):
    return json.loads(json_util.dumps(data))

@app.route("/api/deletequiz", methods=['POST'])
def deletequiz():
    quizname = request.values.get('quizname')
    mycol = db['quiz_cards']
    myquery = {'quizname': quizname}
    mycol.delete_one(myquery)

    mycol = db['quizzes']
    mycol.delete_one(myquery)
    return 'Deleted '+quizname, 200

@app.route("/api/getquizcards")
def get_quiz_cards():
    mycol = db['quiz_cards']
    
    if 'quizname' in request.values:
        query = {'quizname': request.values['quizname']}
        res = mycol.find(query)
        for i in res:
            return parse_json(i)
        return 'No quiz found', 404
    else:
        res = mycol.find()
        r = {"quizcards":[]}
        for i,v in enumerate(res):
            r['quizcards'].append(parse_json(v))
        return r

@app.route("/api/getquiz")
def getquiz():
    mycol = db['quizzes']
    if 'quizname' in request.args:
        query = {'quizname':request.args.get('quizname')}
        res = mycol.find(query)
        for i in res:
            return parse_json(i)

    else:
        return 'enter a valid string please'