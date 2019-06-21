from PIL import Image
import pytesseract
import cv2
import os
import urllib.request
import re
from socialscan.util import Platforms, sync_execute_queries
import string
from collections import defaultdict

with open("english_words.txt", encoding='latin1') as word_file:
    english_words = set(word.strip().lower() for word in word_file)

with open("common_names.txt", encoding='latin1') as names_file:
    common_names = set(name.strip().lower().translate(str.maketrans('', '', name.punctuation)) for name in names_file)

def is_not_english_word(word):
    return not(word.lower() in english_words)

def is_common_name(name):
    name = name.translate(str.maketrans('', '', name.punctuation)) # removes all punctuation from potential name
    return name.lower() in common_names

def read_text(filepath):
    img = cv2.imread(filepath) # opens image
    img = cv2.resize(img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC) # resizes by 1.5x
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) # converts to grayscale
    img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1] # binarizing
    img = cv2.medianBlur(img, 3) # applies blur to remove noise

    cv2.imwrite('temp.png', img) # saves processed post image to defined file name
    img = Image.open('temp.png') # open processed post image
    text = str(pytesseract.image_to_string(img, lang='eng').encode('utf-8')) # reads image and converts bin format to str

    os.remove('temp.png')

    # for word in banned_words:
    #     if re.compile(r'\b({0})\b'.format(word), flags=re.IGNORECASE).search(text): # if banned word is in text
    #         submission.report('Possible banned word {}'.format(word)) # report submission

    if re.compile(r'@([A-Za-z0-9_]+)').search(text): # if twitter username or email present
        # submission.report('Possible identifying information (twitter username or email)')
        return True

    clean_text = text.replace(r'\n', ' ') # replaces newline escapes with whitespace
    clean_text = ' '.join(clean_text.split()) # removes duplicate whitespace
    clean_text = clean_text.split()

    for name in clean_text:
        if is_common_name(name): # if common name in cleaned text
            print('Name found.')

    maybe_usernames = [w for w in clean_text if len(w)>3] # removes words with less than 4 chars
    likely_usernames = [w for w in maybe_usernames if is_not_english_word(w)] # removes words in the english dictionary
    probably_usernames = [w for w in likely_usernames if not w.isdigit()] # removes numbers-only items
    should_be_usernames = [w for w in probably_usernames if re.search(r"[^a-zA-Z0-9\.\_\-]+", w) is None] # removes words with special characters except ., _, and -

    if len(should_be_usernames) <= 5: # if candidates <= 5 (to prevent overloading API)
        platforms = [Platforms.INSTAGRAM, Platforms.SNAPCHAT, Platforms.TUMBLR, Platforms.YAHOO, Platforms.PINTEREST, Platforms.REDDIT] # platforms to check
        results = sync_execute_queries(should_be_usernames, platforms) # checks if username candidates are available on platforms
        
        user_info = []
        for result in results:
            result_info = {}
            if result.available == False: # if username not available, means is valid username
                result_info['username'] = str(result.query)
                result_info['platform'] = str(result.platform)
            if result_info: # if dictionary isn't empty
                user_info.append(result_info)

        consolidated = defaultdict(list)
        for info in user_info:
            consolidated[info['username']].append(info['platform']) # aggregates info by user

        username_found_msg = ''
        for found_username in consolidated:
            string_addon = "The name '{}' was found on: {}. ".format(found_username, ', '.join(consolidated[found_username]))
            username_found_msg += string_addon

# files = 0
# ii_files = 0
# data_dir = os.path.dirname(os.path.abspath(__file__)) + '/data/' # gets directory script is being run from
# for filename in os.listdir(data_dir):
#     if read_text(data_dir + filename):
#         ii_files += 1
#     files += 1

# print('Accuracy is {}%'.format(ii_files/files))
