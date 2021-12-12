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
    executor.submit(make_quiz_huggingface(chapter,quizname, minutes,seconds,filename))
    return 'Successful',200

def make_quiz_old(chapter,quizname, minutes,seconds,filename, summarized_text, keyword_sentence_mapping):

    #get distractors
    count = 0
    keyword_distractor_list = defaultdict(list)
    for keyword in keyword_sentence_mapping:
        d_bow = get_bow2(keyword)
        c = 1 if d_bow else 0
        distractors = get_distractors_conceptnet(keyword) #function to generate distractors form conceptnet.io
        n_distractors = filtered_distractors(keyword,distractors)
        # cl = get_distractors_c(keyword)
        if len(n_distractors)+c>=3:
            if d_bow:
                keyword_distractor_list[keyword] = [d_bow]
            dl = [keyword]+keyword_distractor_list[keyword]+n_distractors[0:3-c]
            keyword_distractor_list[keyword] = dl
            count+=1
            if count>5:
                break
    print('got distractors')
    print(keyword_distractor_list)

    #get meanings
    # distractors = keyword_distractor_list
    distractors = {}
    for keyword,distractor_list in keyword_distractor_list.items():
        list_of_meanings = get_meanings(summarized_text,distractor_list)[0]
        ml = []
        list_of_meanings_all = defaultdict(lambda: None)
        list_of_meanings_all.update(list_of_meanings)
        for d in distractor_list:
            ml.append({'distractor':d,'meaning':list_of_meanings_all[d]})
        random.shuffle(ml)
        distractors[keyword] = ml
    print('got distractors with meanings')


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
        output = pattern.sub( " _______ ", sentence, count=1)
        question_db_val['question'] = output
        question_db_val['distractors'] = distractors[each]
        question_db_val['correct_answer'] = each

        questions.append(question_db_val)
        index += 1
    return questions


def make_quiz_huggingface(chapter,quizname, minutes,seconds,filename):
    text=''
    extension = filename.split('.')[-1]
    if extension == 'pdf':
        #get text from pdf
        text = get_text_tika(filename)
        # print(text)
        text = clean_string(text)
    elif extension == 'txt':
        with open(filename, 'r') as file:
            text = file.read()
    #get summary
    # summarized_text = get_summary_t5(text)
    summarized_text = text
    # summarized_text = get_summary_summa(text,ratio=0.5)
    print('got summary')
    # print(summarized_text)

    #get keywords
    keywords = get_keywords(text, summarized_text)
    print('got keywords')
    print(keywords)

    #get questions
    keyword_sentence_mapping = get_sentences_for_keyword(keywords, summarized_text)
    print('got keyword sentence mapping')
    # print(keyword_sentence_mapping)
    sents = [i[0] for i in keyword_sentence_mapping.values() if i]
    # qa = get_huggingface_questions(sents)
    qa = get_huggingface_questions(sents)
    print('got questions')
    print(qa)
    keyword_qa = {}
    keyword_distractor_list = defaultdict(list)
    for i in qa:
        keyword = i['answer']
        d_bow = get_bow2(keyword)
        c=0
        if d_bow:
            keyword_distractor_list[keyword] = [d_bow]
            c=1
        distractors = get_distractors_conceptnet(keyword) #function to generate distractors form conceptnet.io
        n_distractors = filtered_distractors(keyword,distractors) 
        # cl = get_distractors_c(keyword)
        if len(n_distractors)>=3:
            dl = [keyword]+keyword_distractor_list[keyword]+n_distractors[0:3-c]
            keyword_distractor_list[keyword] = dl
            keyword_qa[keyword] = i
    print('got distractors')
    print(keyword_distractor_list)
    distractors = {}
    for keyword,distractor_list in keyword_distractor_list.items():
        try:
            list_of_meanings = get_meanings(summarized_text,distractor_list)[0]
        except:
            list_of_meanings = {}
        ml = []
        list_of_meanings_all = defaultdict(lambda: None)
        list_of_meanings_all.update(list_of_meanings)
        for d in distractor_list[:4]:
            ml.append({'distractor':d,'meaning':list_of_meanings_all[d]})
        random.shuffle(ml)
        distractors[keyword] = ml
    print('got distractors with meanings')

    quiz_db_val = {'quizname': quizname, 'questions':{}}
    index = 0
    questions=[]
    for each in keyword_qa:
        question_db_val = {'question':"", 'distractors':{}, 'correct_answer':""}
        question_db_val['question'] = keyword_qa[each]['question']
        question_db_val['distractors'] = distractors[each]
        question_db_val['correct_answer'] = each
        questions.append(question_db_val)
        index += 1
        if index>5:
            break
    
    questions += make_quiz_old(chapter, quizname, minutes, seconds, filename, summarized_text, keyword_sentence_mapping)
    n_questions = len(questions)
    quiz_db_val['questions'] = questions
    quiz_card_db_val = {'chapter': chapter,'summarized_text':summarized_text,'quizname': quizname, 'filename':filename,
                'time': {'minutes': minutes, 'seconds': seconds}}
    print(quiz_card_db_val)
    mycol = db['quiz_cards']
    x = mycol.insert_one(quiz_card_db_val)
    print('inserted into cards db')

    mycol = db['quizzes']
    x = mycol.insert_one(quiz_db_val)
    print('inserted into quizzes')

    # update_not taken list of students
    update_all_not_taken(quizname, n_questions)

    return parse_json(quiz_card_db_val)

def update_all_not_taken(quizname, n_questions):
    res = db.student.find()
    for each in res:
        query = {'name': each['name']}
        each['not_taken'].append(quizname)
        each['max_score']+=n_questions
        newvalues = { "$set": each }
        db.student.update_one(query, newvalues)

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
    # res = get_true_false(summarized_text)
    res = generate_tf(summarized_text)
    print('got true false questions')

    # Add True/False questions to dictionary
    questions=quiz_db_val['questions']
    for i in res:
        question_db_val = {'question':"Answer with True/False: \n"+i[0], 'distractors':[{"distractor":"True", 'meaning':None},{"distractor":"False", 'meaning':None}], 'correct_answer':i[1]}
        if i[1] == 'False':
            question_db_val['distractors'][0]['meaning'] = i[2]
        questions.append(question_db_val)
    
    mycol = db['quizzes']
    myquery = { "quizname": quizname}
    newvalues = { "$set": { "questions": questions } }

    mycol.update_one(myquery, newvalues)

    return 'got quiz db val'