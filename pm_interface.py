#TODO: Instead of breaking by using "return" on each error, append all errors and then output
#TODO: Add check for required parameters not being provided

import re
import praw
from prawcore import NotFound

def accept_mod_invites(reddit, message):
    if message.body.startswith('**gadzooks!'):
        sub = reddit.get_info(thing_id=message.subreddit.fullname)
        try:
            sub.accept_moderator_invite()
            return True
        except:
            error = 'Invalid invite.'
            return error
        message.mark_as_read()

def get_sub_config(reddit, message, param_ls_full):
    configs = []
    if message.subject.lower() == '!settings':
        pm = message.body  # gets message body
        pm = pm.replace('\n', ' ').replace('\r', '')  # removes new lines
        pm = ''.join(pm.split()) # removes all whitespace

        try:
            user_args = re.findall(r"\{([^}]*)\}", pm) # finds everything between curly braces
        except AttributeError:
            error = 'Incorrect formatting: No curly braces found.'
            return error

        config = {} # creates dict of chosen config to return from function

        for user_arg in user_args:
            user_arg = user_arg.lower()
            for system_param in param_ls_full:
                system_param = system_param.lower()
                user_param = user_arg[:len(system_param)]
                if system_param == user_param:
                    if user_arg[len(system_param)] == '=': # if there's an equals sign
                        user_setting = user_arg[len(system_param)+1:] # user specified setting is taken as anything beyond equals
                        config[system_param] = user_setting
                    else:
                        config = config.clear() # clears all items from dict
                        error = 'Incorrect formatting: "Equals" symbol (=) is not in the right place.'
                        return error
        
        configs.append(config) # appends sub's config to final list to be checked out
 
    message.mark_read()
    return [config for config in configs if config] # returns config with empty dicts removed

def check(reddit, config, param_ls_full, param_ls_reqd, sub_name):
    '''
    INPUT: Reddit instance, single config
    OUTPUT: True or False depending on whether config passes or fails the check
    '''
    if set(list(config)).issubset(param_ls_reqd) == False: # if all required parameters are not in the config
        error = 'Incorrect value: All required settings have not been provided and/or at least one has been misspelled.'
        return error

    for param in config:
        setting = config[param]
        if param == sub_name:
            if setting[:3] == '/r/':
                setting = setting.replace(param[:3], '') # removes /r/, if present
            elif setting[:2] == 'r/':
                setting = setting.replace(param[:2], '') # removes r/, if present
        else:
            if setting == 'yes':
                setting = True
            elif setting == 'no':
                setting = False
            else:
                error = 'Incorrect value: The setting for parameter "{}" is not a "yes" or "no".'.format(param)
                return error

    sub = config[sub_name] # gets sub name from dict
    try:
        reddit.subreddits.search_by_name(sub, exact=True)
    except NotFound: # if sub does not exist
        error = 'Incorrect value: The specified subreddit does not exist.'
        return error
    
    sub_mods = reddit.subreddit(sub).moderator() # makes list of sub's mods
    equi_bot = praw.models.Redditor(reddit, name='EquivalentBot')
    if equi_bot not in sub_mods: # if not a sub mod
        error = 'Insufficient permissions: EquivalentBot has not been added as a moderator yet.'
        return error

    for mod in sub_mods:
        if mod == equi_bot:
            perms = mod.mod_permissions
            reqd_perms = ['posts', 'mail']
            for req_perm in reqd_perms:
                if req_perm not in perms: # if required perms are not given
                    error = 'Insufficient permissions: EquivalentBot has not been given "{}" perms.'.format(req_perm)
                    return error
                    
    return True
