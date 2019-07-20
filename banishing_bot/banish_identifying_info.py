#TODO: Phone numbers
#TODO: youtube usernames (X days ago)
#TODO: fuzzy algorithm for locations (https://gis.stackexchange.com/a/11456)
#TODO: crossposts
#TODO: allow op name and verified users
#TODO: mention that doesn't work well with half-gibberish
#TODO: mention if username found on a different platform it will be flagged
#TODO: Change mechanism to font-based
#TODO: Get algo to work with optional permissions

from PIL import Image
import pytesseract
import cv2
import os
import urllib.request
import re
from socialscan.util import Platforms, sync_execute_queries
import string
from collections import defaultdict
# import face_recognition
import itertools
import requests
import json

current_dir = os.path.dirname(os.path.abspath(__file__)) # gets directory script is being run from

with open(current_dir + r'\corpora\words_master_list.txt', encoding='latin1') as word_file: # opens file with list of common english words
    stop_words = set(word.lower().strip() for word in word_file) # adds the lower case version of each word to a set

def read_text(filepath, platforms_val, subreddit_check_val, banned_words_val):
    '''
    IN: Path to image to be analyzed
    OUT: Message with analysis of post wrt identifying info
    '''
    img = cv2.imread(filepath) # opens image
    img = cv2.resize(img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC) # resizes by 1.5x to help with OCR
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) # converts to grayscale
    img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1] # binarizing
    img = cv2.medianBlur(img, 3) # applies blur to remove noise

    cv2.imwrite('temp.png', img) # saves processed post image to defined file name
    img = Image.open('temp.png') # open processed post image
    text = str(pytesseract.image_to_string(img, lang='eng').encode('utf-8')) # reads image and converts bin format to str

    os.remove('temp.png') # deletes temp file

    if banned_words_val:
        for word in banned_words_val:
            if re.compile(r'\b({0})\b'.format(word), flags=re.IGNORECASE).search(text): # if banned word is in text
                print('banned word present')

    if 'twitter' in platforms_val:
        if re.compile(r'@([A-Za-z0-9_]+)').search(text): # if twitter username or email present
            return 'Found Twitter username or Email ID' # flags for above condition

    if 'reddit' in platforms_val:
        if re.compile(r'u/([A-Za-z0-9_]+)').search(text):
            return 'Found reddit username'
        if subreddit_check_val:
            if re.compile(r'r/([A-Za-z0-9_]+)').search(text):
                return 'Found subreddit name'

    clean_text = text.replace(r'\n', ' ') # replaces newline escapes with whitespace
    clean_text = ' '.join(clean_text.split()) # removes duplicate whitespace
    clean_text = clean_text.split() # creates list of whitespace separated words
    def no_end_punc(w):
        if w[-1] in ['.', '?', ',']:
            return w[:-1]
        else:
            return w
    clean_text = [no_end_punc(w) for w in clean_text] # trims words where last char is a punctuation
    clean_text = list(dict.fromkeys(clean_text)) # removes duplicates

    username_candidates = [w for w in clean_text if not(w.lower() in stop_words)] # removes "stop words"
    username_candidates = [w for w in username_candidates if len(w)>3] # removes words with less than 4 chars (same reason as above)
    username_candidates = [w for w in username_candidates if not w.isdigit()] # removes numbers-only items (same reason again)
    username_candidates = [w for w in username_candidates if re.search(r"[^a-zA-Z0-9\.\_\-]+", w) is None] # removes words with special characters except ., _, and - (you know the drill)
    URL=r"http://suggestqueries.google.com/complete/search?client=firefox&q="
    headers = {'User-agent':'Mozilla/5.0'}
    for _ in range(5): # 5 retries
        try:
            username_candidates = [w for w in username_candidates if len(json.loads(requests.get(URL+w, headers=headers).content.decode('utf-8'))[1]) <= 3] # removes words with more than 3 autocomplete results
            break
        except TimeoutError as e:
            print(e)
            time.sleep(2)
            pass
    print('username cands', username_candidates)

    if len(username_candidates) <= 10: # if candidates <= 10 (to prevent overloading API)
        platforms = [] # platforms to check
        if 'reddit' in platforms_val:
            platforms.append(Platforms.REDDIT)
        if 'instagram' in platforms_val:
            platforms.append(Platforms.INSTAGRAM)
        if 'snapchat' in platforms_val:
            platforms.append(Platforms.SNAPCHAT)
        if 'tumblr' in platforms_val:
            platforms.append(Platforms.TUMBLR)
        if 'yahoo' in platforms_val:
            platforms.append(Platforms.YAHOO)
        results = sync_execute_queries(username_candidates, platforms) # checks if username candidates are available on platforms
        user_info = [] # makes list to store the queried word's results
        for result in results:
            result_info = {} # makes dictionary for single result (occurrence of one username on one platform)
            if result.available == False: # username not available --> valid username --> is identifying info --> tapsforehead.jpg
                result_info['username'] = str(result.query) # gets the word that was queried and sets as username key
                result_info['platform'] = str(result.platform).lower() # gets the platform it was found on
            if result_info: # if dictionary isn't empty (no available info)
                user_info.append(result_info) # adds single result to list of all results

        consolidated = defaultdict(list) # creates defaultdict to append lists to keys
        for info in user_info:
            consolidated[info['username']].append(info['platform']) # aggregates found platforms by username into a list and pins to the username

        usernames_found = ', '.join([username for username in consolidated])
        unique_platforms_found = ','.join(list(dict.fromkeys(list(itertools.chain.from_iterable([consolidated[username] for username in consolidated])))))

        found_message = "The username(s) {} were found on the platform(s): {}.".format(usernames_found, unique_platforms_found)

        if [username for username in consolidated]:
            return found_message

# def find_faces(filepath):
#     '''
#     IN: Path to image to be analyzed
#     OUT: Coordinates of identified face (if any) on the image
#     '''
#     face_identification_img = face_recognition.load_image_file(filepath) # opens image file as numpy array
#     face_locations = face_recognition.face_locations(face_identification_img)

#     if len(face_locations) > 0: # if the number of faces found is more than 0
#         for face_location in face_locations:
#             # Print the location of each face in this image
#             top, right, bottom, left = face_location
#             return "Face found at Top: {}, Left: {}, Bottom: {}, Right: {}.".format(top, left, bottom, right)
