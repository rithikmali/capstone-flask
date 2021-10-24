from application.app import app,db,executor
from flask import Flask, request
from werkzeug.utils import secure_filename
from pdfminer.high_level import extract_text
import json
import re
import random
from collections import defaultdict
from bson import json_util
import bson
from bson.binary import Binary
from tika import parser 
import collections
from bson.codec_options import CodecOptions
from application.getSummary import *
from application.getKeywords import *
from application.getQuestion import *
from application.getDistractors import *
from application.getMeanings import *
from application.pdftotext import *

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
    filename = ""
    text=''
    try:
        pdf = request.files['file']
        filename = secure_filename(pdf.filename)
        pdf.save(filename)
        text = get_text_pdfminer(filename)
    except:
        print('no pdf')
    
    quiz_card_db_val = {'chapter': chapter,'text':text,'quizname': quizname,
                'pdf': 'pdf', 'time': {'minutes': minutes, 'seconds': seconds}}
    mycol = db['pdfs']
    x = mycol.insert_one(quiz_card_db_val)
    print('inserted into pdf db')
    return 'received form'

def parse_json(data):
    return json.loads(json_util.dumps(data))

@app.route("/api/makequiz", methods=['POST'])
def makequizjob():
    chapter = request.values.get('chapter')
    quizname = request.values.get('quizname')
    minutes = int(request.values.get('minutes'))
    seconds = int(request.values.get('seconds'))
    pdf = request.files['file']
    filename = secure_filename(pdf.filename)
    pdf.save(filename)
    executor.submit(make_quiz(chapter,quizname, minutes,seconds,filename))
    return 'Successful',200

def make_quiz(chapter,quizname, minutes,seconds,filename):
    # if request.method == 'POST':
    #     f = request.files['file']
    #     f.save(secure_filename(f.filename))
    # pdf = request.files['file']
    print(chapter, quizname, minutes, seconds)
    
    print(filename)

    #get text from pdf
    text = get_text_tika(filename)
    # print(text)
    text = clean_string(text)
    #get summary
    # summarized_text = get_summary_t5(text)
    summarized_text = get_summary_summa(text,ratio=0.1)
    print('got summary')
    print(summarized_text)

    #get keywords
    keywords = get_keywords(text, summarized_text)[:4]
    print('got keywords')
    print(keywords)

    #get questions
    keyword_sentence_mapping = get_sentences_for_keyword(keywords, summarized_text)
    print('got keyword sentence mapping')

    # res = get_true_false(summarized_text)
    # print('got true false questions')

    #get distractors
    keyword_distractor_list = defaultdict(list)
    for keyword in keyword_sentence_mapping:
        d_bow = get_bow2(keyword)
        c=0
        if d_bow:
            keyword_distractor_list[keyword] = [d_bow]
            c=1
        distractors = get_distractors_conceptnet(keyword) #function to generate distractors form conceptnet.io
        n_distractors = filtered_distractors(keyword,distractors)
        # cl = get_distractors_c(keyword)
        if len(n_distractors)>=3-c:
            keyword_distractor_list[keyword] = [keyword]+keyword_distractor_list[keyword]+n_distractors[0:3-c]
        print(keyword_distractor_list[keyword])
    print('got distractors')


    #get meanings
    # distractors = keyword_distractor_list
    distractors = {}
    for keyword,distractor_list in keyword_distractor_list.items():
        list_of_meanings = get_meanings(summarized_text,distractor_list)[0]
        ml = []
        list_of_meanings_all = defaultdict(lambda: None)
        list_of_meanings_all |= list_of_meanings
        for d in distractor_list:
            ml.append({'distractor':d,'meaning':list_of_meanings_all[d]})
        random.shuffle(ml)
        distractors[keyword] = ml
    print('got distractors with meanings')

    # Get True/False questions

    # combine everythin into a dictionary
    quiz_db_val = {'quizname': quizname, 'questions':{}}
    index = 1
    questions=[]
    for each in keyword_distractor_list:
        question_db_val = {'question':"", 'distractors':{}, 'correct_answer':""}
        try:
            sentence = keyword_sentence_mapping[each][0]
        except:
            continue
        pattern = re.compile(each, re.IGNORECASE)
        output = pattern.sub( " _______ ", sentence)
        question_db_val['question'] = output
        question_db_val['distractors'] = distractors[each]
        question_db_val['correct_answer'] = each

        questions.append(question_db_val)
        index += 1
    quiz_db_val['questions'] = questions

    # Add True/False questions to dictionary
    # questions=[]
    # for i in res:
    #     question_db_val = {'question':"Answer with True/False: \n"+i[0], 'distractors':["True","False",None,None], 'correct_answer':i[1]}
    #     questions.append(question_db_val)
    #     index += 1
    # quiz_db_val['questions'] = questions

    # print('got quiz db val')


    #insert into cards db
    # quiz_card_db_val = {'chapter': chapter,'summarized_text':summarized_text,'quizname': quizname,
    #             'pdf': pdf, 'time': {'minutes': minutes, 'seconds': seconds}}
    quiz_card_db_val = {'chapter': chapter,'summarized_text':summarized_text,'quizname': quizname,
                'pdf': filename, 'time': {'minutes': minutes, 'seconds': seconds}}
    mycol = db['quiz_cards']
    x = mycol.insert_one(quiz_card_db_val)
    print('inserted into cards db')

    #inserting into questions db
        # TODO
    mycol = db['quizzes']
    x = mycol.insert_one(quiz_db_val)
    print('inserted into quizzes')

    return parse_json(quiz_card_db_val)

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

@app.route("/api/addtruefalse")
def addtruefalse():
    quizname = request.args.get('quizname')
    mycol = db['quizzes']
    query = {'quizname':quizname}
    res = mycol.find(query)
    quiz_db_val = None
    for i in res:
        quiz_db_val = i
    
    mycol = db['quiz_cards']
    query = {'quizname':quizname}
    res = mycol.find(query)
    quiz_card_db_val = None
    for i in res:
        quiz_card_db_val = i

    summarized_text = quiz_card_db_val['summarized_text']
    res = get_true_false(summarized_text)
    print('got true false questions')

    # Add True/False questions to dictionary
    questions=quiz_db_val['questions']
    for i in res:
        question_db_val = {'question':"Answer with True/False: \n"+i[0], 'distractors':["True","False",None,None], 'correct_answer':i[1]}
        questions.append(question_db_val)
    
    mycol = db['quizzes']
    myquery = { "quizname": quizname}
    newvalues = { "$set": { "questions": questions } }

    mycol.update_one(myquery, newvalues)

    return 'got quiz db val'