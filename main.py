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

os.environ['reddit_username'] = 'banishing_bot'
os.environ['reddit_password']= 'loldummy321!!'
os.environ['client_id'] = '7lYA3JuVLtRnLw'
os.environ['client_secret'] = 'v4GLi0_9PbkE6N3bSMdgjHaCReU'
os.environ['user_agent'] = 'EquivalentAI v0.1'

# Retrieve heroku env variables
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

param_ls_full = ['subreddit_name', 'faces_check'] # lists all parameters of the bot (optional included)

subreddit_name = param_ls_full[0]
face_check = param_ls_full[1]

param_ls_reqd = [subreddit_name, face_check] # lists all required parameters
reqd_perms = ['posts'] # lists all required permissions

while True: # loops back around to keep streams running
    print('Monitoring inbox...')
    unread_configs = []
    for message in reddit.inbox.stream(skip_existing=True, pause_after=-1): # gets stream of new inbox messages
        if message is None: # if no new message at this point
            break

        print('Evaluating message...')
        pmi = pm_interface.Interface(reddit, message, param_ls_full, param_ls_reqd)
        message_author = reddit.redditor(message.author.name)

        print('Checking invite...')
        invite_info = pmi.accept_mod_invites()
        if invite_info != True: # if invalid invite
            message_author.message('banishing_bot: Error in your PM.', invite_info)
            continue # skips to next iteration

        print('Extracting sub config...')
        unread_config = pmi.extract_sub_config()
        if type(unread_config) == str: # if error message is returned (lazy code, I know)
            message_author.message('banishing_bot: Error in your PM.', unread_config)
            continue

        print('Checking sub config...')
        check_info = pmi.check_and_correct(unread_config, subreddit_name, reqd_perms)
        if check_info: # if there are no failed checks
            unread_configs.append(unread_config)
        else:
            message_author.message('banishing_bot: Error in your PM.', check_info)
            continue

    print('Attempting to download new configurations...')
    with open('local_configs.txt', 'a+') as f: # updates locally saved configs
        print('Reading previous configurations...')
        try:
            local_configs = eval(f.readline())
        except SyntaxError:
            local_configs = []

        print('Going through new configurations and running past previous ones.')
        for u_config in unread_configs:
            for l_config in local_configs:
                if u_config[subreddit_name] == l_config[subreddit_name]: # if the same sub has sent another config
                    local_configs[local_configs.index(l_config)] = u_config # updates local_config index accordingly
                    unread_configs.remove(u_config) # removes item from new_configs
        for u_config in unread_configs:
            local_configs.append(u_config) # appends all remaining items (new configurations)

        print('Clearing old version of file...')
        f.seek(0)
        f.truncate()
        print('Saving locally...')
        f.write(str(local_configs))

    f.close() # closes text file

    if local_configs:
        print('Initializing multireddit...')
        multireddit = reddit.multireddit('banishing_bot', 'empty_sub_init') # instantiates multireddit class
        subs_to_monitor = [config[subreddit_name] for config in local_configs] # gets names of all the subs to be streamed
        for subreddit in subs_to_monitor:
            try:
                multireddit.add(subreddit) # adds subreddits to be monitored in multireddit
            except Exception as e:
                print(e)
                print('/r/{} probably does not exist.'.format(subreddit))
        
        print('Monitoring multireddit...')
        for submission in multireddit.stream.submissions(pause_after=-1):
            if submission is None: # same logic as in inbox
                break

            print('Getting relevant configuration details...')
            relevant_config = dict(filter(lambda config: config[subreddit_name] == str(submission.subreddit), local_configs)) # gets config for the sub the post's been streamed
            face_check_val = relevant_config[face_check] # gets face check value

            print('Scraping submission...')
            url = submission.url
            IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff'} # lists accepted formats
            if posixpath.splitext(urllib.parse.urlparse(url).path)[1] in IMAGE_EXTS: # if it's an image
                print('Downloading image...')
                try:
                    current_dir = os.path.dirname(os.path.abspath(__file__)) # gets directory script is being run from
                    filename = current_dir + str(submission.id) + '.png' # defines path to download to
                    urllib.request.urlretrieve(url, filename) # downloads image to defined path
                except urllib.error.HTTPError as e: # if image has been deleted
                    print(e)
                    print('Probably broken link.')
                    continue
                
                print('Reading text for identifying information...')
                text_report = bii.read_text(filename)
                if text_report: # if a report was output by the function
                    if len(text_report) > 100: # reports greater than 100 characters long throw exceptions
                        text_report = text_report[:97] + '...' # trims report and adds ellipsis
                    submission.report(text_report)

                print('Scanning post for faces...')
                if face_check_val:
                    face_report = bii.find_faces(filename)
                    if face_report:
                        submission.report(face_report)

                os.remove(filename)
        else:
            break