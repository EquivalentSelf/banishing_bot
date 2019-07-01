#TODO: Add nuke as a separate function run by messaging bot

import praw
import os
import re
import importlib
import pickle

import pm_interface
import banish_identifying_info as bii 

# Retrieve heroku env variables
reddit_username = os.environ['reddit_username']
reddit_password = os.environ['reddit_password']
client_id = os.environ['client_id']
client_secret = os.environ['client_secret']

reddit = praw.Reddit(client_id=client_id,
                     client_secret=client_secret,
                     user_agent='EquivalentAI v1.0',
                     username=reddit_username,
                     password=reddit_password)

param_ls_full = ['subreddit_name', 'faces_check'] # lists all parameters of the bot (optional included)

subreddit_name = param_ls_full[0]
face_check = param_ls_full[1]

param_ls_reqd = [subreddit_name] # lists all required parameters

unread_configs = []
for message in reddit.inbox.unread():
    pmi = pm_interface.Interface(reddit, message)

    invite_info = pmi.accept_mod_invites()
    if invite_info != True: # if invalid invite
        print(invite_info)
        continue # skips to next iteration

    unread_config = pmi.extract_sub_config(param_ls_full)
    if type(unread_config) == str: # if error message is returned (lazy code, I know)
        print(unread_config)
        continue

    check_info = pmi.check_and_correct(unread_config, subreddit_name)
    if check_info: # if there are no failed checks
        unread_configs.append(unread_config)
    else:
        print(check_info)
        continue

with open('local_configs.txt', 'rb+') as f:
    try:
        local_configs = pickle.load(f)
    except EOFError: # if pickle file is empty
        local_configs = []

    for n_config in unread_configs:
        for l_config in local_configs:
            if n_config[subreddit_name] == l_config[subreddit_name]: # if the same sub has sent another config
                local_configs[local_configs.index(l_config)] = n_config # updates local_config
                new_configs.remove(n_config) # removes item from new_configs
    for n_config in new_configs:
        local_configs.append(n_config) # appends all remaining items

    pickle.dump(local_configs)

for updated_config in local_configs:
    sub = updated_config[subreddit_name]
    face_check_val = updated_config[face_check]
    # n_posts = updated_config[]
    # if n_posts >= 1000: n_posts = None
    # banned_words = updated_config[]
    # removal_reason_p = updated_config[]
    # age_p = updated_config[]
    # thresh_p = updated_config[]
    # removal_reason_c = updated_config[]
    # age_c = updated_config[]
    # thresh_c = updated_config[]

    # for submission in reddit.subreddit(sub).new(limit=n_posts):
    #     if post_thresh_val: # runs removal functions first
    #         thresh_remove.post_threshold_remove(reddit, sub, submission, removal_reason_p, age_p, thresh_p)
    #     if comment_thresh_bool:
    #         thresh_remove.comment_threshold_remove(reddit, sub, submission, removal_reason_c, age_c, thresh_c)
    #     if ocr_val:
    #         ocr_mod.run_scan(submission, banned_words)
