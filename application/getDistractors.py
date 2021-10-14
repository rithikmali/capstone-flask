


# Distractors from http://conceptnet.io/
def get_distractors_conceptnet(word):
    import requests
    import json
    import re

    def get_obj(word):
        url = "http://api.conceptnet.io/query?node=/c/en/%s/n&rel=/r/IsA&start=/c/en/%s&limit=2"%(word,word)
        obj = requests.get(url).json()

        if not obj['edges']:
            url = "http://api.conceptnet.io/query?node=/c/en/%s/n&rel=/r/DerivedFrom&start=/c/en/%s&limit=2"%(word,word)
            obj = requests.get(url).json()
        
        if not obj['edges']:
            url = "http://api.conceptnet.io/query?node=/c/en/%s/n&rel=/r/RelatedTo&start=/c/en/%s&limit=2"%(word,word)
            obj = requests.get(url).json()

        if not obj['edges']:
            url = "http://api.conceptnet.io/query?node=/c/en/%s/n&rel=/r/MannerOf&start=/c/en/%s&limit=2"%(word,word)
            obj = requests.get(url).json()

        return obj

    word = word.lower()
    original_word= word
    if (len(word.split())>0):
        word = word.replace(" ","_")
    distractor_list = [] 
    # url = "http://api.conceptnet.io/query?node=/c/en/%s/n&rel=/r/PartOf&start=/c/en/%s&limit=5"%(word,word)
    obj = get_obj(word)

    # print(word)
    # print("\tobj1 :", obj)
    
    for edge in obj['edges']:
        link = edge['end']['term'] 

        url2 = "http://api.conceptnet.io/query?node=%s&rel=/r/RelatedTo&end=%s&limit=10&other=/c/en"%(link,link)
        obj2 = requests.get(url2).json()
        # obj2 = get_obj(link)
        # print("\t\tedge",edge,"\n\t\t  obj2", obj2)
        for edge in obj2['edges']:
            word2 = edge['start']['label']
            if word2 not in distractor_list and original_word.lower() not in word2.lower():
                distractor_list.append(word2)
    return distractor_list

def filtered_distractors(keyw, dl):
    import inflect
    dl = [x.lower() for x in dl]
    dl = list(set(dl))
    p = inflect.engine()
    filtered_dl = [keyw]
    for word1 in dl:
        is_dup=0
        for word2 in filtered_dl:
            if p.compare(word1, word2):
                is_dup=1 
                break     
            if p.compare_nouns(word1, word2):
                is_dup=1
                break
            if p.compare_verbs(word1, word2):
                is_dup=1
                break
            if p.compare_adjs(word1, word2):
                is_dup=1
                break
        if not is_dup:
            filtered_dl.append(word1)
    filtered_dl.remove(keyw)
    return filtered_dl

def get_bow(word):
    import spacy
    import numpy as np
    from numba import jit
    nlp = spacy.load("en_core_web_lg")

    @jit(nopython=True)
    def cosine_similarity_numba(u:np.ndarray, v:np.ndarray):
        assert(u.shape[0] == v.shape[0])
        uv = 0
        uu = 0
        vv = 0
        for i in range(u.shape[0]):
            uv += u[i]*v[i]
            uu += u[i]*u[i]
            vv += v[i]*v[i]
        cos_theta = 1
        if uu != 0 and vv != 0:
            cos_theta = uv/np.sqrt(uu*vv)
        return cos_theta

    def most_similar(word, topn=5):
        word = nlp.vocab[str(word)]
        queries = [
            w for w in word.vocab 
            if w.is_lower == word.is_lower and w.prob >= -15 and np.count_nonzero(w.vector)
        ]

        by_similarity = sorted(queries, key=lambda w: cosine_similarity_numba(w.vector, word.vector), reverse=True) 
        # print(by_similarity)
        return [(w.lower_,w.similarity(word)) for w in by_similarity[:topn+1] if w.lower_ != word.lower_]

    r = most_similar(word, topn=3)
    return r

def get_distractors_c(word):
    def word2vec(word):
        from collections import Counter
        from math import sqrt

        # count the characters in word
        cw = Counter(word)
        # precomputes a set of the different characters
        sw = set(cw)
        # precomputes the "length" of the word vector
        lw = sqrt(sum(c*c for c in cw.values()))

        # return a tuple
        return cw, sw, lw

    def cosdis(v1, v2):
        # which characters are common to the two words?
        common = v1[1].intersection(v2[1])
        # by definition of cosine distance we have
        return sum(v1[0][ch]*v2[0][ch] for ch in common)/v1[2]/v2[2]
    
    def distractor1(correct_answer):
        from wordhoard import Antonyms
        antonym = Antonyms(correct_answer)
        va=word2vec(correct_answer)
        antonym_results = antonym.find_antonyms()
        sim=[]
        #print(antonym_results)
        for j in antonym_results:
            vb = word2vec(j)
            sim.append((j,cosdis(va,vb)))
        #print(sorted(sim,key = lambda x: x[1],reverse=True))
        antonym_results = sorted(sim,key = lambda x: x[1],reverse=True)
        return antonym_results[0][0]
    
    def distractor3():
        from random_word import RandomWords
        r = RandomWords()
        d = r.get_random_word(hasDictionaryDef="true", includePartOfSpeech="noun,verb", minCorpusCount=1, maxCorpusCount=10, minDictionaryCount=1, maxDictionaryCount=10, minLength=5, maxLength=10)
        return d
    
    # return [distractor1(word),get_bow(word),distractor3()]
    return [distractor1(word),distractor3(),distractor3()]