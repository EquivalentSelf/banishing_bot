#TODO: Banned words
#TODO: Ensure only compatible image formats are allowed
#TODO: youtube usernames
#TODO: fuzzy algorithm for locations (https://gis.stackexchange.com/a/11456)
#TODO: API limit
#TODO: allow crossposts

from PIL import Image
import pytesseract
import cv2
import os
import urllib.request
import re
from socialscan.util import Platforms, sync_execute_queries
import string
from collections import defaultdict
import face_recognition

current_dir = os.path.dirname(os.path.abspath(__file__)) # gets directory script is being run from

with open(current_dir + r'\corpora\english_words.txt', encoding='latin1') as word_file: # opens file with list of common english words
    english_words = set(word.lower().strip() for word in word_file) # adds the lower case version of each word to a set
word_file.close()

with open(current_dir + r'\corpora\common_names.txt', encoding='latin1') as names_file: # opens file with list of common first names
    common_names = set(name.strip().lower().translate(str.maketrans('', '', string.punctuation)) for name in names_file) # removes punctuation from names in file and adds them to a set
names_file.close()

def is_not_english_word(word):
    '''
    IN: String that could be a common word
    OUT: Boolean of if the string is **not** an english word
    '''
    return not(word.lower() in english_words)

def is_common_name(name):
    '''
    IN: String that could be a common name
    OUT: Boolean of if the string is a common name
    '''
    return name.lower() in common_names

def read_text(filepath):
    '''
    IN: Path to image to be analyzed
    OUT: 
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

    # for word in banned_words:
    #     if re.compile(r'\b({0})\b'.format(word), flags=re.IGNORECASE).search(text): # if banned word is in text
    #         submission.report('Possible banned word {}'.format(word)) # report submission

    if re.compile(r'@([A-Za-z0-9_]+)').search(text): # if twitter username or email present
        return 'Twitter username or Email ID' # flags for above condition

    clean_text = text.replace(r'\n', ' ') # replaces newline escapes with whitespace
    clean_text = ' '.join(clean_text.split()) # removes duplicate whitespace
    clean_text = clean_text.split() # creates list of whitespace separated words

    maybe_usernames = [w for w in clean_text if is_not_english_word(w)] # removes words in the english dictionary (unlikely to be usernames or names)
    likely_usernames = [w for w in maybe_usernames if len(w)>3] # removes words with less than 4 chars (same reason as above)
    probably_usernames = [w for w in likely_usernames if not w.isdigit()] # removes numbers-only items (same reason again)
    should_be_usernames = [w for w in probably_usernames if re.search(r"[^a-zA-Z0-9\.\_\-]+", w) is None] # removes words with special characters except ., _, and - (you know the drill)

    names_found = [] # creates list to append all found names
    for name in maybe_usernames: 
        name = name.translate(str.maketrans('', '', string.punctuation)) # removes all punctuation from potential name
        if is_common_name(name): # if common name in cleaned text
            names_found.append(name) # appends to list of found names
    if names_found:
        return 'First names found: {}'.format(', '.join(names_found))

    usernames_found = '' # instantiates initial string to append output to
    if len(should_be_usernames) <= 10: # if candidates <= 5 (to prevent overloading API)
        platforms = [Platforms.INSTAGRAM, Platforms.SNAPCHAT, Platforms.TUMBLR, Platforms.YAHOO, Platforms.REDDIT] # platforms to check
        results = sync_execute_queries(should_be_usernames, platforms) # checks if username candidates are available on platforms
        
        user_info = [] # makes list to store the queried word's results
        for result in results:
            result_info = {} # makes dictionary for single result (occurrence of one username on one platform)
            if result.available == False: # username not available --> valid username --> is identifying info --> tapsforehead.jpg
                result_info['username'] = str(result.query) # gets the word that was queried and sets as username key
                result_info['platform'] = str(result.platform) # gets the platform it was found on
            if result_info: # if dictionary isn't empty (no available info)
                user_info.append(result_info) # adds individual result to list of results

        consolidated = defaultdict(list) # creates defaultdict to append lists to keys
        for info in user_info:
            consolidated[info['username']].append(info['platform']) # aggregates info by user into a list and pins to a key

        for username in consolidated: # for each valid user in the list
            add_on = "The username '{}' was found on: {}. ".format(username, ', '.join(consolidated[username])) # creates string with info on where the user was found
            usernames_found += add_on # appends user info to output string and moves to next username in dict

        if usernames_found:
            return usernames_found

def find_faces(filepath):
    '''
    IN: Path to image to be analyzed
    OUT: Coordinates of identified face (if any) on the image
    '''
    face_identification_img = face_recognition.load_image_file(filepath) # opens image file as numpy array
    face_locations = face_recognition.face_locations(face_identification_img)

    if len(face_locations) > 0: # if the number of faces found is more than 0
        for face_location in face_locations:
            # Print the location of each face in this image
            top, right, bottom, left = face_location
            return "Face located at pixel location Top: {}, Left: {}, Bottom: {}, Right: {}".format(top, left, bottom, right)
