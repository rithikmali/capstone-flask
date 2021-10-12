
def get_summary_deepai(text):
    import requests
    r = requests.post(
        "https://api.deepai.org/api/summarization",
        data={
            'text': text,
        },
        headers={'api-key': 'quickstart-QUdJIGlzIGNvbWluZy4uLi4K'}
    )
    return r.json()

def get_summary_t5(text):
    import torch
    from transformers import T5ForConditionalGeneration,T5Tokenizer
    summary_model = T5ForConditionalGeneration.from_pretrained('t5-base')
    summary_tokenizer = T5Tokenizer.from_pretrained('t5-base')

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    summary_model = summary_model.to(device)
    import nltk
    # nltk.download('punkt')
    # nltk.download('brown')
    # nltk.download('wordnet')
    from nltk.corpus import wordnet as wn
    from nltk.tokenize import sent_tokenize

    def postprocesstext (content):
        final=""
        for sent in sent_tokenize(content):
            sent = sent.capitalize()
            final = final +" "+sent
        return final


    def summarizer(text,model,tokenizer):
        text = text.strip().replace("\n"," ")
        text = "summarize: "+text
        # print (text)
        max_len = 512
        encoding = tokenizer.encode_plus(text,max_length=max_len, pad_to_max_length=False,truncation=True, return_tensors="pt").to(device)

        input_ids, attention_mask = encoding["input_ids"], encoding["attention_mask"]

        outs = model.generate(input_ids=input_ids,
                                        attention_mask=attention_mask,
                                        early_stopping=True,
                                        num_beams=3,
                                        num_return_sequences=1,
                                        no_repeat_ngram_size=2,
                                        min_length = 75,
                                        max_length=300)


        dec = [tokenizer.decode(ids,skip_special_tokens=True) for ids in outs]
        summary = dec[0]
        summary = postprocesstext(summary)
        summary= summary.strip()

        return summary


    summarized_text = summarizer(text,summary_model,summary_tokenizer)
    return summarized_text

if __name__ == '__main__':
    text = '''The incident ray, the normal at the point of incidence and the reflected are all in this plane. Bob greene: when you bend the paper you create a plane
different from the plane in which incident and normal lie - this indicates that incident, normal and reflection all lie in the same plane, he says.
It's another law of reflection.'''
    st = get_summary_t5(text)
    print(st)