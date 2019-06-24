#TODO: Add nuke as a separate function run by messaging bot

import praw
import os
import re
import importlib
import pickle

pm_interface = importlib.import_module('pm_interface.py')
ocr_mod = importlib.import_module('ocr.py')
thresh_remove = importlib.import_module('threshold_remove.py')

# Retrieve heroku env variables
reddit_username = os.environ['reddit_username']
reddit_password = os.environ['reddit_password']
client_id = os.environ['client_id']
client_secret = os.environ['client_secret']

reddit = praw.Reddit(client_id=client_id,
                     client_secret=client_secret,
                     user_agent='EquivalentBot v1.0 (by EquivalentSelf)',
                     username=reddit_username,
                     password=reddit_password)

param_ls_full = ['sub', 'banned words scan', 'post threshold remove', 'comment threshold remove', 
'n posts', 'banned words', 'posts removal reason', ''] # lists all parameters of the bot (optional included)

sub_name = param_ls_full[0]
ocr_bool = param_ls_full[1]
post_thresh_bool = param_ls_full[2]
comment_thresh_bool = param_ls_full[3]

param_ls_reqd = [sub_name, ocr_bool] # lists all required parameters

new_configs = []
for message in reddit.inbox.unread():
    invite_info = pm_interface.accept_mod_invites(reddit, message)
    if invite_info != True: # if invalid invite
        print(invite_info)
        continue

    config_info = pm_interface.get_sub_config(reddit, message, param_ls_full, param_ls_reqd, sub_name)
    if type(config_info) != list: # if error message is returned
        print(config_info)
        continue

    check_info = pm_interface.check(reddit, config_info)
    if check_info: # if there are no failed checks
        new_configs.append(config_info)
    else:
        print(check_info)
        continue

with open('local_configs.txt', 'rb+') as f:
    try:
        local_configs = pickle.load(f)
    except EOFError: # if pickle file is empty
        local_configs = []

    for n_config in new_configs:
        for l_config in local_configs:
            if n_config[sub_name] == l_config[sub_name]: # if the same sub has sent another config
                local_configs[local_configs.index(l_config)] = n_config # updates local_config
                new_configs.remove(n_config) # removes item from new_configs
    for n_config in new_configs:
        local_configs.append(n_config) # appends all remaining items

    pickle.dump(local_configs)

for updated_config in local_configs:
    sub = updated_config[sub_name]
    ocr_val = updated_config[ocr_bool]
    post_thresh_val = updated_config[post_thresh_bool]
    comment_thresh_val = updated_config[comment_thresh_bool]
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
