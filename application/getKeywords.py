def get_keywords(original_text, summarized_text):
    from flashtext import KeywordProcessor
    import nltk
    from nltk.corpus import stopwords
    import string
    import pke
    import traceback

    def get_nouns_multipartite(content):
        out=[]
        try:
            extractor = pke.unsupervised.MultipartiteRank()
            extractor.load_document(input=content)
            #    not contain punctuation marks or stopwords as candidates.
            pos = {'PROPN','NOUN'}
            #pos = {'PROPN','NOUN'}
            stoplist = list(string.punctuation)
            stoplist += ['-lrb-', '-rrb-', '-lcb-', '-rcb-', '-lsb-', '-rsb-']
            stoplist += stopwords.words('english')
            extractor.candidate_selection(pos=pos, stoplist=stoplist)
            extractor.candidate_weighting(alpha=1.1,
                                            threshold=0.75,
                                            method='average')
            keyphrases = extractor.get_n_best(n=15)
            

            for val in keyphrases:
                out.append(val[0])
        except:
            out = []
            traceback.print_exc()

        return out

    keywords = get_nouns_multipartite(original_text)
    # print ("keywords found in unsummarized: ",keywords)
    keyword_processor = KeywordProcessor()
    for keyword in keywords:
        keyword_processor.add_keyword(keyword)

    keywords_found = keyword_processor.extract_keywords(summarized_text)
    keywords_found = list(set(keywords_found))
    print ("keywords found in summarized: ",keywords_found)

    important_keywords =[]
    for keyword in keywords:  
        if keyword in keywords_found:
            important_keywords.append(keyword)

    return important_keywords