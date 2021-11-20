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
    return 'Deleted '+ quizname, 200

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


@app.route("/api/register", methods=['POST'])
def register_student():
    mycol = db['student']
    r = dict(request.values)
    if request.is_json:
        r2 = dict(request.get_json())
        r|=r2
    if mycol.find_one({'name':r['name']}):
        return 'Student is already registered', 400
    mycol.insert_one(r)
    return 'Student registered', 200 


@app.route("/api/student", methods=['GET'])
def get_student():
    mycol = db['student']
    r = dict(request.values)
    if request.is_json:
        r2 = dict(request.get_json())
        r|=r2
    if 'name' in r:
        query = {'name': r['name']}
        res = mycol.find_one(query)
        if res:
            return parse_json(res)
        return 'No student found', 404
    else:
        res = mycol.find()
        ret = {"students":[]}
        for v in res:
            ret['students'].append(parse_json(v))
        return ret

@app.route("/api/report", methods=['GET'])
def get_report():
    mycol = db['report']
    r = dict(request.values)
    if request.is_json:
        r2 = dict(request.get_json())
        r|=r2
    if 'name' in r:
        query = {'name': r['name']}
        res = mycol.find_one(query)
        if res:
            if 'quizname' not in r:
                return parse_json(res)
            
            for i in res['quizzes']:
                if i['quizname'] == r['quizname']:
                    return parse_json(i)

        return 'No report found', 404
    else:
        return 'Enter student name', 400

@app.route("/api/addreport", methods=['POST'])
def add_report():
    mycol = db['report']
    r = dict(request.values)
    if request.is_json:
        r2 = dict(request.get_json())
        r|=r2
    query = {'name': r['name']}
    res = mycol.find_one(query)
    new = r['quizzes']

    if res:
        report = res
        quizname = r['quizzes'][0]['quizname']
        for i in range(len(report['quizzes'])):
            if report['quizzes'][i]['quizname'] == quizname:
                report['quizzes'][i] = r['quizzes'][0]
                break
        else:
            report['quizzes'] += r['quizzes']
        newvalues = { "$set": { "quizzes": report['quizzes'] } }
        mycol.update_one(query, newvalues)
        
        user = db['student'].find_one(query)
        user['total_score'] += r['quizzes'][0]['score']
        if quizname in user['not_taken']:
            user['not_taken'].remove(quizname)
        user['taken'].append(quizname)

        newvalues = { "$set": user }
        db['student'].update_one(query,newvalues)

        return 'Updated', 200
    else:
        # report = {'name':r['name'] ,'quizzes': [new]}
        not_taken = []
        all_max_scores = []
        res = db['quiz_cards'].find()
        for i in res:
            q = {'quizname': i['quizname']}
            quiz = db['quizzes'].find_one(q)
            all_max_scores.append(len(quiz['questions']))
            not_taken.append(i['quizname'])
        quizname = r['quizzes'][0]['quizname']
        not_taken.remove(quizname)
        r['max_score'] = sum(all_max_scores)
        # r['total_score'] = r['quizzes'][0]['score']
        mycol.insert_one(r)
        mycol = db['student']
        a = {'name':r['name'], 'not_taken': not_taken, 'taken':[quizname], 'total_score':r['quizzes'][0]['score'],'max_score':sum(all_max_scores)}
        mycol.insert_one(a)
        return 'Inserted new report', 200
