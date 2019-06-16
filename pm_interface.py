import praw

def accept_mod_invites(reddit):
    for message in reddit.get_unread():
        if message.body.startswith('**gadzooks!'):
            sr = reddit.get_info(thing_id=message.subreddit.fullname)
            try:
                sr.accept_moderator_invite()
            except praw.errors.InvalidInvite:
                continue
            message.mark_as_read()

def get_sub_config(reddit):
    for message in reddit.inbox.messages():
        if message.subject == '!BotquivalentSelf':
            reddit.reddit_session.get_my_moderation()
            text = message.text
            if 'Sub name' in text:
                sub_name = text[len('Sub name'):]
