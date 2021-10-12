

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
            keyword_sentences[key].append(sentence)

    for key in keyword_sentences.keys():
        values = keyword_sentences[key]
        values = sorted(values, key=len, reverse=True)
        keyword_sentences[key] = values
    return keyword_sentences
