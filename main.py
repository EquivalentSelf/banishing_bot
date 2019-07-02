# send nice mail on join
# run parallel streams

import praw
import os
import re
import pickle
import posixpath
import urllib.parse
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

param_ls_reqd = [subreddit_name, face_check] # lists all required parameters
reqd_perms = ['posts'] # lists all required permissions

unread_configs = []
for message in reddit.inbox.stream(): # gets stream of new inbox messages
    pmi = pm_interface.Interface(reddit, message, param_ls_full, param_ls_reqd)

    invite_info = pmi.accept_mod_invites()
    if invite_info != True: # if invalid invite
        print(invite_info)
        continue # skips to next iteration

    unread_config = pmi.extract_sub_config()
    if type(unread_config) == str: # if error message is returned (lazy code, I know)
        print(unread_config)
        continue

    check_info = pmi.check_and_correct(unread_config, subreddit_name, reqd_perms)
    if check_info: # if there are no failed checks
        unread_configs.append(unread_config)
    else:
        print(check_info)
        continue

with open('local_configs.txt', 'rb+') as f: # updates locally saved configs
    try:
        local_configs = pickle.load(f)
    except EOFError: # if pickle file is empty
        local_configs = []

    for n_config in unread_configs:
        for l_config in local_configs:
            if n_config[subreddit_name] == l_config[subreddit_name]: # if the same sub has sent another config
                local_configs[local_configs.index(l_config)] = n_config # updates local_config index accordingly
                unread_configs.remove(n_config) # removes item from new_configs
    for n_config in unread_configs:
        local_configs.append(n_config) # appends all remaining items (new configurations)

    pickle.dump(local_configs)

multireddit = reddit.multireddit() # instantiates multireddit class
subs_to_monitor = [config[subreddit_name] for config in local_configs] # gets names of all the subs to be streamed
for subreddit in subs_to_monitor:
    try:
        multireddit.add(subreddit) # adds subreddits to be monitored in multireddit
    except Exception as e:
        print(e)
        print('/r/{} probably does not exist.'.format(subreddit))

IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff'} # lists accepted formats
current_dir = os.path.dirname(os.path.abspath(__file__)) # gets directory script is being run from
for submission in reddit.multireddit().stream.submissions():
    relevant_config = dict(filter(lambda config: config[subreddit_name] == str(submission.subreddit), local_configs)) # gets config for the sub the post's been streamed
    face_check_val = relevant_config[face_check] # gets face check value

    url = submission.url
    submission_id = submission.id
    if posixpath.splitext(urllib.parse.urlparse(url).path)[1] in IMAGE_EXTS: # if image
        try:
            filename = current_dir + str(submission_id) + '.png' # defines path to download to
            urllib.request.urlretrieve(url, filename) # downloads image to defined path
        except urllib.error.HTTPError as e: # if image has been deleted
            print(e)
            print('Probably broken link.')
            continue
        
        text_report = bii.read_text(filename)
        if text_report: # if a report was output by the function
            submission.report(text_report)

        if face_check_val:
            face_report = bii.find_faces(filename)
            if face_report:
                submission.report(face_report)

        os.remove(filename)
