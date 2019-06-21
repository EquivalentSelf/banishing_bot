import praw
import os
import re

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

sub = 'comedyheaven' # sub to operate in


