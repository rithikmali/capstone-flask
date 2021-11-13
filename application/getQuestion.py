

from os import name


def get_sentences_for_keyword(keywords, summarized_text):
    from nltk.tokenize import sent_tokenize
    from flashtext import KeywordProcessor

    def tokenize_sentences(text):
        sentences = [sent_tokenize(text)]
        sentences = [y for x in sentences for y in x]
        # Remove any short sentences less than 10 letters. and sentences that are question
        sentences = [sentence.strip() for sentence in sentences if ( (len(sentence) > 10 ) and ('?' not in sentence))]
        return sentences
    
    sentences = tokenize_sentences(summarized_text)

    keyword_processor = KeywordProcessor()
    keyword_sentences = {}
    for word in keywords:
        keyword_sentences[word] = []
        keyword_processor.add_keyword(word)
    for sentence in sentences:
        keywords_found = keyword_processor.extract_keywords(sentence)
        for key in keywords_found:
            if not keyword_sentences[key]:
                keyword_sentences[key].append(sentence)
                break

    for key in keyword_sentences.keys():
        values = keyword_sentences[key]
        values = sorted(values, key=len, reverse=True)
        keyword_sentences[key] = values
    return keyword_sentences

def get_true_false(summarized_text):
    import string
    from string import punctuation
    import nltk
    from nltk import tokenize
    from nltk.tokenize import sent_tokenize
    import re
    import benepar
    import spacy
    import torch
    import random
    print('in get_true_false')
    benepar_parser = benepar.Parser("benepar_en3")
    nlp = spacy.load('en_core_web_lg')

    def preprocess(sentences):
        output = []
        for sent in sentences:
            single_quotes_present = len(re.findall(r"['][\w\s.:;,!?\\-]+[']",sent))>0
            double_quotes_present = len(re.findall(r'["][\w\s.:;,!?\\-]+["]',sent))>0
            question_present = "?" in sent
            if single_quotes_present or double_quotes_present or question_present :
                continue
            else:
                output.append(sent.strip(punctuation))
        return output

    candidate_sents_list = tokenize.sent_tokenize(summarized_text)
    candidate_sents_list = [re.split(r'[:;]+',x)[0] for x in candidate_sents_list ]
    # Remove very short sentences less than 30 characters and long sentences greater than 150 characters
    cand_sents = [sent for sent in candidate_sents_list if len(sent)>40 and len(sent)<150]
    filter_quotes_and_questions = preprocess(cand_sents)
    print("got filter quotes and questions",filter_quotes_and_questions)

    def get_flattened(t):
        sent_str_final = None
        if t is not None:
            sent_str = [" ".join(x.leaves()) for x in list(t)]
            sent_str_final = [" ".join(sent_str)]
            sent_str_final = sent_str_final[0]
        return sent_str_final
    

    def get_termination_portion(main_string,sub_string):
        combined_sub_string = sub_string.replace(" ","")
        main_string_list = main_string.split()
        last_index = len(main_string_list)
        for i in range(last_index):
            check_string_list = main_string_list[i:]
            check_string = "".join(check_string_list)
            check_string = check_string.replace(" ","")
            if check_string == combined_sub_string:
                return " ".join(main_string_list[:i])
                        
        return None
        
    def get_right_most_VP_or_NP(parse_tree,last_NP = None,last_VP = None):
        if len(parse_tree.leaves()) == 1:
            return get_flattened(last_NP),get_flattened(last_VP)
        last_subtree = parse_tree[-1]
        if last_subtree.label() == "NP":
            last_NP = last_subtree
        elif last_subtree.label() == "VP":
            last_VP = last_subtree
        
        return get_right_most_VP_or_NP(last_subtree,last_NP,last_VP)


    def get_sentence_completions(key_sentences):
        sentence_completion_dict = {}
        for individual_sentence in filter_quotes_and_questions:
            sentence = individual_sentence.rstrip('?:!.,;')
            tree = benepar_parser.parse(sentence)
            last_nounphrase, last_verbphrase =  get_right_most_VP_or_NP(tree)
            phrases= []
            if last_verbphrase is not None:
                verbphrase_string = get_termination_portion(sentence,last_verbphrase)
                if verbphrase_string is not None:
                    phrases.append(verbphrase_string)
            if last_nounphrase is not None:
                nounphrase_string = get_termination_portion(sentence,last_nounphrase)
                if nounphrase_string is not None:
                    phrases.append(nounphrase_string)
            print(phrases)
            longest_phrase =  sorted(phrases, key=len,reverse= True)
            if len(longest_phrase) == 2:
                first_sent_len = len(longest_phrase[0].split())
                second_sentence_len = len(longest_phrase[1].split())
                if (first_sent_len - second_sentence_len) > 4:
                    del longest_phrase[1]
                    
            if len(longest_phrase)>0:
                sentence_completion_dict[sentence]=longest_phrase
        return sentence_completion_dict

    sent_completion_dict = get_sentence_completions(filter_quotes_and_questions)
    print("Sentence completion dict", sent_completion_dict)

    from transformers import pipeline, set_seed
    generator = pipeline('text-generation', model='gpt2')
    set_seed(42)

    # add the EOS token as PAD token to avoid warnings
    
    from sentence_transformers import SentenceTransformer
    # Load the BERT model. Various models trained on Natural Language Inference (NLI) https://github.com/UKPLab/sentence-transformers/blob/master/docs/pretrained-models/nli-models.md and 
    # Semantic Textual Similarity are available https://github.com/UKPLab/sentence-transformers/blob/master/docs/pretrained-models/sts-models.md
    model_BERT = SentenceTransformer('bert-base-nli-mean-tokens')

    from nltk import tokenize
    import scipy
    torch.manual_seed(2020)


    def sort_by_similarity(original_sentence,generated_sentences_list):
        # Each sentence is encoded as a 1-D vector with 768 columns
        sentence_embeddings = model_BERT.encode(generated_sentences_list)

        queries = [original_sentence]
        query_embeddings = model_BERT.encode(queries)
        # Find the top sentences of the corpus for each query sentence based on cosine similarity
        number_top_matches = len(generated_sentences_list)

        dissimilar_sentences = []

        for query, query_embedding in zip(queries, query_embeddings):
            distances = scipy.spatial.distance.cdist([query_embedding], sentence_embeddings, "cosine")[0]

            results = zip(range(len(distances)), distances)
            results = sorted(results, key=lambda x: x[1])


            for idx, distance in reversed(results[0:number_top_matches]):
                score = 1-distance
                if score < 0.9:
                    dissimilar_sentences.append(generated_sentences_list[idx].strip())
            
        sorted_dissimilar_sentences = sorted(dissimilar_sentences, key=len)
        
        return sorted_dissimilar_sentences[:3]
        

    def generate_sentences(partial_sentence,full_sentence):
        # input_ids = torch.tensor([tokenizer.encode(partial_sentence)])
        # maximum_length = len(partial_sentence.split())+80

        # Actiavte top_k sampling and top_p sampling with only from 90% most likely words
        # sample_outputs = model.generate(
        #     input_ids, 
        #     do_sample=True, 
        #     max_length=maximum_length, 
        #     top_p=0.90, # 0.85 
        #     top_k=50,   #0.30
        #     repetition_penalty  = 10.0,
        #     num_return_sequences=10
        # )
        generated_sentences=generator(partial_sentence, max_length=50, num_return_sequences=5)
        generated_sentences = [i['generated_text'] for i in generated_sentences]
        
        # for i, sample_output in enumerate(sample_outputs):
        #     decoded_sentences = tokenizer.decode(sample_output, skip_special_tokens=True)
        #     decoded_sentences_list = tokenize.sent_tokenize(decoded_sentences)
        #     generated_sentences.append(decoded_sentences_list[0])
        # import requests
        # r = requests.post(
        #     "https://api.deepai.org/api/text-generator",
        #     data={
        #         'text': 'YOUR_TEXT_HERE',
        #     },
        #     headers={'api-key': 'quickstart-QUdJIGlzIGNvbWluZy4uLi4K'}
        # )
            
        top_3_sentences = sort_by_similarity(full_sentence,generated_sentences)
        
        return top_3_sentences

    index = 1
    res = []
    for key_sentence in sent_completion_dict:
        partial_sentences = sent_completion_dict[key_sentence]
        res.append([(key_sentence,"True")])
        print('For loop',key_sentence,"True")
        false_sentences =[]
        for partial_sent in partial_sentences[:1]:
            false_sents = generate_sentences(partial_sent,key_sentence)
            print(false_sents)
            false_sentences.extend(false_sents)
        for i in false_sentences[:1]:
            res[-1].append((i,'False'))
        index+=1
    res = [random.choice(i) for i in random.sample(res,3)]
    return res

def generate_tf(summarized_text):
    import torch
    import transformers
    import tensorflow as tf
    import requests
    import json
    from summa.summarizer import summarize
    import benepar
    import string
    import nltk
    from nltk import tokenize
    from nltk.tokenize import sent_tokenize
    import re
    from random import shuffle
    import spacy
    nlp = spacy.load('en_core_web_sm')
#this package is required for the summa summarizer
    nltk.download('punkt')
    benepar.download('benepar_en3')
    benepar_parser = benepar.Parser("benepar_en3")
    from string import punctuation

    def preprocess(sentences):
        output = []
        for sent in sentences:
            single_quotes_present = len(re.findall(r"['][\w\s.:;,!?\\-]+[']",sent))>0
            double_quotes_present = len(re.findall(r'["][\w\s.:;,!?\\-]+["]',sent))>0
            question_present = "?" in sent
            if single_quotes_present or double_quotes_present or question_present :
                continue
            else:
                output.append(sent.strip(punctuation))
        return output
            
            
    def get_candidate_sents(resolved_text, ratio=0.3):
        candidate_sents = summarize(resolved_text, ratio=ratio)
        print(candidate_sents)
        candidate_sents_list = tokenize.sent_tokenize(candidate_sents)
        candidate_sents_list = [re.split(r'[:;]+',x)[0] for x in candidate_sents_list ]
        # Remove very short sentences less than 30 characters and long sentences greater than 150 characters
        filtered_list_short_sentences = [sent for sent in candidate_sents_list if len(sent)>30 and len(sent)<150]
        return filtered_list_short_sentences

    cand_sents = get_candidate_sents(summarized_text)
    filter_quotes_and_questions = preprocess(cand_sents)
        
    def get_flattened(t):
        sent_str_final = None
        if t is not None:
            sent_str = [" ".join(x.leaves()) for x in list(t)]
            sent_str_final = [" ".join(sent_str)]
            sent_str_final = sent_str_final[0]
        return sent_str_final
        

    def get_termination_portion(main_string,sub_string):
        combined_sub_string = sub_string.replace(" ","")
        main_string_list = main_string.split()
        last_index = len(main_string_list)
        for i in range(last_index):
            check_string_list = main_string_list[i:]
            check_string = "".join(check_string_list)
            check_string = check_string.replace(" ","")
            if check_string == combined_sub_string:
                return " ".join(main_string_list[:i])
                        
        return None
        
    def get_right_most_VP_or_NP(parse_tree,last_NP = None,last_VP = None):
        if len(parse_tree.leaves()) == 1:
            return get_flattened(last_NP),get_flattened(last_VP)
        last_subtree = parse_tree[-1]
        if last_subtree.label() == "NP":
            last_NP = last_subtree
        elif last_subtree.label() == "VP":
            last_VP = last_subtree
        
        return get_right_most_VP_or_NP(last_subtree,last_NP,last_VP)


    def get_sentence_completions(key_sentences):
        sentence_completion_dict = {}
        for individual_sentence in filter_quotes_and_questions:
            sentence = individual_sentence.rstrip('?:!.,;')
            tree = benepar_parser.parse(sentence)
            last_nounphrase, last_verbphrase =  get_right_most_VP_or_NP(tree)
            phrases= []
            if last_verbphrase is not None:
                verbphrase_string = get_termination_portion(sentence,last_verbphrase)
                phrases.append(verbphrase_string)
            if last_nounphrase is not None:
                nounphrase_string = get_termination_portion(sentence,last_nounphrase)
                phrases.append(nounphrase_string)

            longest_phrase =  sorted(phrases, key=len,reverse= True)
            if len(longest_phrase) == 2:
                first_sent_len = len(longest_phrase[0].split())
                second_sentence_len = len(longest_phrase[1].split())
                if (first_sent_len - second_sentence_len) > 4:
                    del longest_phrase[1]
                    
            if len(longest_phrase)>0:
                sentence_completion_dict[sentence]=longest_phrase
        return sentence_completion_dict
    
    from transformers import GPT2LMHeadModel, GPT2Tokenizer
    tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

    # add the EOS token as PAD token to avoid warnings
    model = GPT2LMHeadModel.from_pretrained("gpt2",pad_token_id=tokenizer.eos_token_id)

    from sentence_transformers import SentenceTransformer
    # Load the BERT model. Various models trained on Natural Language Inference (NLI) https://github.com/UKPLab/sentence-transformers/blob/master/docs/pretrained-models/nli-models.md and 
    # Semantic Textual Similarity are available https://github.com/UKPLab/sentence-transformers/blob/master/docs/pretrained-models/sts-models.md
    model_BERT = SentenceTransformer('bert-base-nli-mean-tokens')

    sent_completion_dict = get_sentence_completions(filter_quotes_and_questions)

    from nltk import tokenize
    import scipy
    torch.manual_seed(2020)


    def sort_by_similarity(original_sentence,generated_sentences_list):
        # Each sentence is encoded as a 1-D vector with 768 columns
        sentence_embeddings = model_BERT.encode(generated_sentences_list)

        queries = [original_sentence]
        query_embeddings = model_BERT.encode(queries)
        # Find the top sentences of the corpus for each query sentence based on cosine similarity
        number_top_matches = len(generated_sentences_list)

        dissimilar_sentences = []

        for query, query_embedding in zip(queries, query_embeddings):
            distances = scipy.spatial.distance.cdist([query_embedding], sentence_embeddings, "cosine")[0]

            results = zip(range(len(distances)), distances)
            results = sorted(results, key=lambda x: x[1])


            for idx, distance in reversed(results[0:number_top_matches]):
                score = 1-distance
                if score < 0.9:
                    dissimilar_sentences.append(generated_sentences_list[idx].strip())
            
        sorted_dissimilar_sentences = sorted(dissimilar_sentences, key=len)
        
        return sorted_dissimilar_sentences[:3]
        

    def generate_sentences(partial_sentence,full_sentence):
        input_ids = torch.tensor([tokenizer.encode(partial_sentence)])
        maximum_length = len(partial_sentence.split())+80

        # Actiavte top_k sampling and top_p sampling with only from 90% most likely words
        sample_outputs = model.generate(
            input_ids, 
            do_sample=True, 
            max_length=maximum_length, 
            top_p=0.90, # 0.85 
            top_k=50,   #0.30
            repetition_penalty  = 10.0,
            num_return_sequences=10
        )
        generated_sentences=[]
        for i, sample_output in enumerate(sample_outputs):
            decoded_sentences = tokenizer.decode(sample_output, skip_special_tokens=True)
            decoded_sentences_list = tokenize.sent_tokenize(decoded_sentences)
            generated_sentences.append(decoded_sentences_list[0])
            
        top_3_sentences = sort_by_similarity(full_sentence,generated_sentences)
        
        return top_3_sentences
    import random
    index = 1
    choice_list = ["a)","b)","c)","d)","e)","f)"]
    final_sentences = []
    for key_sentence in sent_completion_dict:
        partial_sentences = sent_completion_dict[key_sentence]
        false_sentences =[]
        curr = []
        # print_string = "**%s) True Sentence (from the story) :**"%(str(index))
        # printmd(print_string)
        curr.append([key_sentence, 'True'])
        for partial_sent in partial_sentences:
            false_sents = generate_sentences(partial_sent,key_sentence)
            curr.extend([[sent, 'False'] for sent in false_sents])
        random_sent = random.choice(curr)
        if random_sent[1] == 'False':
            random_sent.append(curr[0][0])
        final_sentences.append(random_sent)
        index = index+1
    return final_sentences


if __name__ == "__main__":
    text = "There is a lot of volcanic activity at divergent plate boundaries in the oceans. For example, many undersea volcanoes are found along the Mid-Atlantic Ridge. This is a divergent plate boundary that runs north-south through the middle of the Atlantic Ocean. As tectonic plates pull away from each other at a divergent plate boundary, they create deep fissures, or cracks, in the crust. Molten rock, called magma, erupts through these cracks onto Earth’s surface. At the surface, the molten rock is called lava. It cools and hardens, forming rock. Divergent plate boundaries also occur in the continental crust. Volcanoes form at these boundaries, but less often than in ocean crust. That’s because continental crust is thicker than oceanic crust. This makes it more difficult for molten rock to push up through the crust. Many volcanoes form along convergent plate boundaries where one tectonic plate is pulled down beneath another at a subduction zone. The leading edge of the plate melts as it is pulled into the mantle, forming magma that erupts as volcanoes. When a line of volcanoes forms along a subduction zone, they make up a volcanic arc. The edges of the Pacific plate are long subduction zones lined with volcanoes. This is why the Pacific rim is called the “Pacific Ring of Fire.”"
    res = get_true_false(text)
    print(res)