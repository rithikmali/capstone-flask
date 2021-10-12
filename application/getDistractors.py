


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
        