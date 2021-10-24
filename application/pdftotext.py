
def get_text_pdfminer(pdf_path):
    text = extract_text(pdf_path)
    return text

def get_text_tika(pdf_path):
    from tika import parser
    raw = parser.from_file(pdf_path)
    return raw['content']

def clean_string(text):
    import string
    valid = string.printable
    refined_text = [character for character in text if character in valid]
    final_text = "".join(refined_text)

    #Removes blank lines
    lines = final_text.split("\n")
    non_empty_lines = [line for line in lines if line.strip() != ""]
    string_without_empty_lines = ""
    for line in non_empty_lines:
        string_without_empty_lines += line + "\n"
    
    import re

    regex = r"Fig. [0-9]*\.[0-9]*( :(.*\n)?)?"
    subst = ""
    test_str = string_without_empty_lines
    # You can manually specify the number of replacements by changing the 4th argument
    result = re.sub(regex, subst, test_str, 0)

    regex = r"Activity [0-9]*\.[0-9]"
    test_str = result
    result = re.sub(regex, subst, test_str, 0)

    regex = r"Exercises(.*\n*)*"
    test_str = result
    result = re.sub(regex, subst, test_str, 0)
    result = result.replace("\n", " ")

    # regex = r"\.( (.*\n*)\?)"
    # test_str = result.replace('\n'," ")
    # result = re.sub(regex, ".", test_str, 0)
    import nltk
    words = set(nltk.corpus.words.words())

    result = " ".join(w for w in nltk.wordpunct_tokenize(result) \
            if w.lower() in words or not w.isalpha())

    return result