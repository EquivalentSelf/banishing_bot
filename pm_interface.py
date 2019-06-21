import praw

def accept_mod_invites(reddit):
    for message in reddit.get_unread():
        if message.body.startswith('**gadzooks!'):
            sub = reddit.get_info(thing_id=message.subreddit.fullname)
            try:
                sub.accept_moderator_invite()
            except:
                print('Error: Invalid invite')
            message.mark_as_read()

def get_sub_config(reddit):
    my_subs = list(reddit.user.moderator_subreddits())
    for message in reddit.inbox.messages():
        if message.subject == '!BotquivalentSelf':
            pm_text = message.text
            
