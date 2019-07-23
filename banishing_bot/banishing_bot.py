#TODO: send nice mail on join with configuration details
#TODO: trim face found report message
#TODO: migrate pm_interface to website

import praw
import os
import re
import posixpath
import urllib.parse
import time
import itertools
import numpy as np
import psycopg2

import pm_interface
import banish_identifying_info as bii
from db_interface import send_and_receive_configs

# Retrieves heroku env variables
reddit_username = os.environ['reddit_username']
reddit_password = os.environ['reddit_password']
client_id = os.environ['client_id']
client_secret = os.environ['client_secret']
user_agent = os.environ['user_agent']

reddit = praw.Reddit(client_id=client_id,
                     client_secret=client_secret,
                     user_agent=user_agent,
                     username=reddit_username,
                     password=reddit_password)

print('Running...')

param_ls = ['subreddit_name', 'banned_words', 'platforms', 'subreddit_check'] # lists all parameters of the bot
# param_ls = ['subreddit_name', 'banned_words', 'platforms', 'subreddit_check', 'faces_check']
optional_param_ls = ['subreddit_check', 'banned_words'] # lists optional params
param_ls_reqd = list(set(param_ls) - set(optional_param_ls)) # sets reqd perms as not optional params
reqd_perms = ['posts'] # lists required permissions

subreddit_name_param = param_ls[0]
banned_words_param = param_ls[1]
platforms_param = param_ls[2]
subreddit_check_param = param_ls[3]
# face_check_param = param_ls[4]

last_scan = None
while True: # loops back around to keep streams running
    print('Monitoring inbox...')
    unread_configs = []
    for message in reddit.inbox.messages(limit=None): # gets inbox messages
        print(message.body)
        error_message_contents = [] # creates list for storing all error messages
        pmi = pm_interface.Interface(reddit, message, param_ls, param_ls_reqd, subreddit_check_param) # initializes PM interface
        message_author = reddit.redditor(message.author.name) # gets sender of PM
        
        unread_config = []
        if message.body.startswith('**gadzooks!'): # if mod invite
            invite_info = pmi.accept_mod_invites() # try to accept the invite
            if isinstance(invite_info, str): # if invalid invite (lazy code)
                error_message_contents.append(invite_info) # adds to error list
        elif message.subject.lower() == '!settings':
            unread_config_info = pmi.extract_sub_config() # extracts sub config
            if unread_config_info[1]: # if there are errors
                unread_config = [] # sets unread configs as empty (as if there are no new configs)
                error_message_contents.append(unread_config_info[1]) # adds to error list
            else: # if all checks are passed
                unread_config = unread_config_info[0] # assigns as unread config

        if unread_config: # if there are unread configs
            check_info = pmi.check_and_correct(unread_config, subreddit_name_param, platforms_param, reqd_perms, banned_words_param) # runs through more checks
            if check_info[1]: # if the error list returned is not empty
                error_message_contents.append(check_info[1]) # adds to error list
            else: # if all checks are passed
                unread_configs.append(check_info[0]) # adds to unread configs list

        if error_message_contents: # if there are error messages
            if len(np.shape(error_message_contents)) != 1 or np.shape(error_message_contents)[0] > 1: # if not 1 dimensional
                error_message_contents = list(itertools.chain.from_iterable(error_message_contents)) # flattens list
            message_author.message('banishing_bot: Error in your PM.', '\n'.join(error_message_contents)) # PMs error messages on a line each
    
        last_scan = time.time() # sets last scan as the current time

    if unread_configs:
        print('Reading and updating local configurations...')
        local_configs = send_and_receive_configs(reddit, unread_configs, subreddit_name_param)

    if local_configs:
        print('Monitoring multireddit...')
        subs_to_monitor = [l_config[subreddit_name_param] for l_config in local_configs] # gets names of all the subs that have submitted configs
        subs_to_monitor_str =  "+".join(subs_to_monitor)
        
        for submission in reddit.subreddit(subs_to_monitor_str).mod.unmoderated(limit=None): # gets unmod queue items
            if last_scan is not None and submission.created_utc < last_scan: # if submission was made before the last scan, exits the loop
                break
            
            relevant_config = next((config for config in local_configs if config[subreddit_name_param] == str(submission.subreddit).lower()), False) # gets config for the sub from which the post came
            
            if relevant_config: # if the sub has added a config
                platforms_val = relevant_config[platforms_param] # gets platforms to check for II
                # face_check_val = relevant_config[face_check_param] # gets face check value
                try: # optional parameters raise an error
                    subreddit_check_val = relevant_config[subreddit_check_param] # gets sub name check param
                except KeyError:
                    subreddit_check_val = []
                try:
                    banned_words_val = relevant_config[banned_words_param] # gets banned words param
                except KeyError:
                    banned_words_val = []

                url = submission.url # gets submission url
                IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff'} # lists compatible formats
                if posixpath.splitext(urllib.parse.urlparse(url).path)[1] in IMAGE_EXTS: # if compatible format
                    try:
                        current_dir = os.path.dirname(os.path.abspath(__file__)) # gets directory script is being run from
                        filename = current_dir + str(submission.id) + '.png' # defines path to download to
                        urllib.request.urlretrieve(url, filename) # downloads image to defined path
                    except urllib.error.HTTPError as e: # if image has been deleted/leads to a broken link
                        print('Probably broken link.')
                        continue # skips to next post
                    
                    print('Reading text for identifying information...')
                    text_report = bii.read_text(filename, platforms_val, subreddit_check_val, banned_words_val)
                    if text_report is not None: # if a report was output by the function
                        if len(text_report) > 100: # reports greater than 100 characters long throw exceptions
                            text_report = text_report[:97] + '...' # trims report and adds ellipsis
                        # submission.report(text_report)
                        print(url+text_report)

                    # print('Scanning post for faces...')
                    # if face_check_val is not None: # if a face was found by the function
                    #     face_report = bii.find_faces(filename)
                    #     if face_report:
                    #         # submission.report(face_report)
                    #         print(url+face_report)

                    os.remove(filename)

            last_scan = time.time() # sets last scan as the current time
    
    print('Sleeping...')
    time.sleep(4)