from application.app import app,db
from flask import Flask, request
from pdfminer.high_level import extract_text
import json
import re
from bson import json_util

from application.getSummary import *
from application.getKeywords import *
from application.getQuestion import *
from application.getDistractors import *

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
    chapter = request.args.get('chapter')
    quizname = request.args.get('quizname')
    no_of_questions = request.args.get('no_of_questions')

    #get text from pdf
    text = get_text(pdf_path)
    # print(text)
    
    #get summary
    summarized_text = get_summary_t5(text)
    print('got summary')

    #get keywords
    keywords = get_keywords(text, summarized_text)
    print('got keywords')

    #get questions
    keyword_sentence_mapping = get_sentences_for_keyword(keywords, summarized_text)
    print('got keyword sentence mapping')

    #get distractors
    keyword_distractor_list = {}
    for keyword in keyword_sentence_mapping:
        distractors = get_distractors_conceptnet(keyword) #function to generate distractors form conceptnet.io
        n_distractors = filtered_distractors(keyword,distractors)
        if len(n_distractors)>=3:
            keyword_distractor_list[keyword] = [keyword]+n_distractors[:3]
    print('got distractors')


    #get meanings
    distractors = keyword_distractor_list
    # distractors = {}
    # for distractor_list in keyword_distractor_list.values():
    #     distractors[keyword] = get_meanings(summarized_text,distractor_list)

    # print('got distractors with meanings')


    #combine everythin into a dictionary
    quiz_db_val = {'quizname': quizname, 'questions':{}}
    index = 1
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

        quiz_db_val['questions'][str(index)] = question_db_val
        index += 1
    print('got quiz db val')


    #insert into cards db
    quiz_card_db_val = {'chapter': chapter,'summarized_text':summarized_text,'quizname': quizname,
                'no_of_questions': no_of_questions, 'pdf': 'pdf'}
    mycol = db['quiz_cards']
    x = mycol.insert_one(quiz_card_db_val)
    print('inserted into cards db')

    #inserting into questions db
        # TODO
    mycol = db['quizzes']
    x = mycol.insert_one(quiz_db_val)
    print('inserted into quizzes')

    return parse_json(quiz_card_db_val)

@app.route("/getquizcards")
def get_quiz_cards():
    mycol = db['quiz_cards']
    res = mycol.find()
    r = {}
    for i,v in enumerate(res):
        r[i]=parse_json(v)
    return r

@app.route("/getquiz")
def getquiz():
    mycol = db['quizzes']
    if 'quizname' in request.args:
        query = {'quizname':request.args.get('quizname')}
        res = mycol.find(query)
        for i in res:
            return parse_json(i)

    else:
        return 'enter a valid string please'