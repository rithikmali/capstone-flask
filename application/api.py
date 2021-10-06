from application.app import app,db
from flask import Flask, request
from application.getSummary import *
from pdfminer.high_level import extract_text
import json
from bson import json_util

@app.route("/")
def home():
    return {"Status": "Success"}, 200 

# Write your API endpoints here

def get_text(pdf_path):
    text = extract_text(pdf_path)
    return text

def parse_json(data):
    return json.loads(json_util.dumps(data))

@app.route("/makequiz")
def make_quiz():
    # if request.method == 'POST':
    #     f = request.files['file']
    #     f.save(secure_filename(f.filename))
    pdf_path = request.args.get('path')
    chapter = request.args.get('c')
    text = get_text(pdf_path)
    print(text)
    # summarized_text = get_summary_deepai(text)
    summarized_text = get_summary_t5(text)
    
    #insert into db
    db_val = {'chapter': chapter,'summarized_text':summarized_text}
    mycol = db['quiz']
    x = mycol.insert_one(db_val)

    return parse_json(db_val)

@app.route("/getquiz")
def get_quiz():
    c = 0
    mycol = db['quiz']
    if 'chapter' in request.args:
        query = {'chapter':request.args.get('chapter')}
        res = mycol.find(query)
        c=1
    else:
        res = mycol.find()


    if c:
        for i in res:
            return parse_json(i)
    else:
        r = {}
        for i,v in enumerate(res):
            r[i]=parse_json(v)
        if r:
            return r
    return 'enter a valid string please'