#TODO: Add check for required parameters not being provided
#TODO: Test if edits to dictionary here affects main

import re
import praw
from prawcore import NotFound

class Interface:
    def __init__(self, reddit, message, param_ls_full, param_ls_reqd):
        self.reddit = reddit
        self.message = message
        self.param_ls_full = param_ls_full
        self.param_ls_reqd = self.param_ls_reqd

    def accept_mod_invites(self):
        if self.message.body.startswith('**gadzooks!'):
            sub = self.reddit.get_info(thing_id=self.message.subreddit.fullname)
            try:
                sub.accept_moderator_invite()
                return True
            except:
                invalid_invite_check = 'Invalid invite.'
                return invalid_invite_check
            self.message.mark_as_read()

    def extract_sub_config(self):
        '''
        INPUT: Full list parameters
        OUTPUT: Formatting error messages or user config (values not checked)
        '''
        if self.message.subject.lower() == '!settings':
            pm = self.message.body  # gets message body
            pm = pm.replace('\n', ' ').replace('\r', '')  # removes new lines
            pm = ''.join(pm.split()) # removes all whitespace

            curly_check = ''
            try:
                user_args = re.findall(r"\{([^}]*)\}", pm) # finds everything between curly braces and adds to list
            except AttributeError:
                curly_check = 'Incorrect formatting: No curly braces found.'

            config = {} # creates dict of chosen config to return from function

            equals_check = ''
            for user_arg in user_args:
                user_arg = user_arg.lower() # lower-cases user argument
                for system_param in self.param_ls_full:
                    system_param = system_param.lower() # lower-cases parameter (just in case)
                    user_param = user_arg[:len(system_param)] # gets setting by user for parameter
                    if system_param == user_param:
                        if user_arg[len(system_param)] == '=': # if there's an equals sign in the right place
                            user_setting = user_arg[len(system_param)+1:] # user specified setting is taken as anything beyond equals
                            config[system_param] = user_setting # adds to configuration dict with system parameter as key
                        else:
                            config = config.clear() # clears all items from dict
                            equals_check = 'Incorrect formatting: "Equals" symbol (=) is not in the right place.'    
        self.message.mark_read()

        if curly_check or equals_check:
            return curly_check + '\n' + equals_check
        else:
            return config # returns config

    def check_and_correct(self, config, sub_name_param, reqd_perms):
        '''
        INPUT: Single config, list of all parameters, list of mandatory parameters, element in sys param list that represents the sub name
        OUTPUT: Error message if config fails the check
        '''
        all_params_check = ''
        other_settings_check = ''
        sub_exist_check = ''
        sub_mod_check = ''
        req_perm_check = ''

        if set(list(config)).issubset(self.param_ls_reqd) == False: # if all required parameters are not in the config
            all_params_check = 'Incorrect value: All required settings have not been provided and/or at least one has been misspelled.'

        for param in config: # translates to a standard format
            setting = config[param]
            if param == sub_name_param: # if the field is for the subreddit name
                if setting[:3] == '/r/':
                    setting = setting.replace(param[:3], '') # removes /r/, if present
                elif setting[:2] == 'r/':
                    setting = setting.replace(param[:2], '') # removes r/, if present
            else:
                if setting == 'enable':
                    setting = True # makes boolean
                elif setting == 'disable':
                    setting = False
                else:
                    other_settings_check = 'Incorrect value: The setting for "{}" is not "enable" or "disable".'.format(param)

        sub = config[sub_name_param] # gets sub name from dict
        try:
            self.reddit.subreddits.search_by_name(sub, exact=True)
        except NotFound: # if sub does not exist
            sub_exist_check = 'Incorrect value: The specified subreddit does not exist.'
        
        sub_mods = self.reddit.subreddit(sub).moderator() # makes list of sub's mods
        banishing_bot = praw.models.Redditor(self.reddit, name='banishing_bot')
        if banishing_bot not in sub_mods: # if not a sub mod
            sub_mod_check = 'Insufficient permissions: banishing_bot has not been added as a moderator yet.'

        for mod in sub_mods:
            if mod == banishing_bot:
                perms = mod.mod_permissions
                for req_perm in reqd_perms:
                    if req_perm not in perms: # if required perms are not given
                        req_perm_check = 'Insufficient permissions: banishing_bot has not been given "{}" perms.'.format(req_perm)

        return [all_params_check, other_settings_check, sub_exist_check, sub_mod_check, req_perm_check]