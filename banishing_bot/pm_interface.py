import re
import praw
from prawcore import NotFound

class Interface:
    def __init__(self, reddit, message, param_ls, param_ls_reqd, sub_check_param):
        self.reddit = reddit
        self.message = message
        self.param_ls = param_ls
        self.param_ls_reqd = param_ls_reqd
        self.subreddit_check_param = sub_check_param

    def accept_mod_invites(self):
        try:
            self.message.subreddit.mod.accept_moderator_invite()
            return True
        except:
            return 'Invalid moderator invite.'
        return False

    def extract_sub_config(self):
        '''
        INPUT: None
        OUTPUT: Formatting error messages and user config (values not fully checked)
        '''
        error_checks = []

        config = {} # creates dict of chosen config to return from function
        pm = self.message.body  # gets message body
        pm = pm.replace('\n', ' ').replace('\r', '')  # removes new lines
        pm = ''.join(pm.split()) # removes all whitespace

        try:
            user_args = re.findall(r"\{([^}]*)\}", pm) # finds everything between curly braces and adds to list
        except AttributeError:
            error_checks.append('Incorrect formatting: No curly braces found.')

        for user_arg in user_args:
            if user_arg:
                user_arg = user_arg.lower() # lower-cases user argument
                for system_param in self.param_ls:
                    system_param = system_param.lower() # lower-cases parameter (just in case)
                    user_param = user_arg[:len(system_param)] # gets setting by user for parameter (if length correct)
                    if system_param == user_param:
                        if '=' in user_arg:
                            user_setting = user_arg.split("=", 1)[1] # user specified setting is taken as anything beyond equals
                            if user_arg != user_setting:
                                if user_setting:
                                    config[system_param] = user_setting
                                else:
                                    error_checks.append('Incorrect value: "{}" has been assigned an empty value.'.format(system_param))
                            else: # if split fails because of no delimiter
                                    config = config.clear() # clears all items from dict
                                    error_checks.append('Incorrect formatting: "Equals" symbol (=) is not in the right place.')
                        else:
                            error_checks.append('Incorrect formatting: "Equals" symbol (=) is not present in at least one parameter.')
            else:
                error_checks.append('Incorrect formatting: Empty curly braces found.')

        return [config, error_checks]

    def check_and_correct(self, config, sub_name_param, platforms_param, reqd_perms, banned_words_param):
        '''
        INPUT: Single config, element in param ls for sub name, element in param ls for platforms, required perms
        OUTPUT: Value error messages and checked config
        '''

        error_checks = []
        if set(self.param_ls_reqd).issubset(set(list(config))) == False: # if all required parameters are not in the config
            print('FALSE')
            error_checks.append('Incorrect value: All required settings have not been provided and/or at least one has been misspelled.')
            return [config, error_checks] # can't go on with checks without all required settings provided

        if 'reddit' in config[platforms_param] and self.subreddit_check_param not in list(config):
            error_checks.append('Incorrect value: "reddit" has been specified as a platform but a value for subreddit_check is not given.')

        for param in config: # translates to a standard format
            user_setting = config[param]
            if user_setting: # if not an empty string
                if param == sub_name_param: # if the field is for the subreddit name
                    if user_setting[:3] == '/r/':
                        config[param] = user_setting.replace(param[:3], '') # removes /r/, if present
                    elif user_setting[:2] == 'r/':
                        config[param] = user_setting.replace(param[:2], '') # removes r/, if present
                elif param == platforms_param:
                    user_platforms = user_setting.split(",")
                    supported_platforms = ['instagram', 'snapchat', 'tumblr', 'yahoo', 'reddit']
                    for p in user_platforms:
                        if p not in supported_platforms:
                            error_checks.append('Incorrect value: The setting for "{}" is not in the correct format and/or includes an unsupported platform.'.format(param))
                    config[param] = user_platforms
                elif param == banned_words_param:
                    config[param] = user_setting.split(",")
                else:
                    if user_setting == 'enabled':
                        config[param] = True # standardizes to boolean
                    elif user_setting == 'disabled':
                        config[param] = False
                    else:
                        error_checks.append('Incorrect value: The setting for "{}" is not "enabled" or "disabled".'.format(param))
            else:
                error_checks.append('Missing value: The setting for "{}" is not specified.'.format(param))

        sub_name = config[sub_name_param] # gets sub name from dict
        try:
            self.reddit.subreddits.search_by_name(sub_name, exact=True)
        except NotFound: # if sub does not exist
            error_checks.append('Incorrect value: The specified subreddit does not exist.')
            return [config, error_checks] # can't go on with next checks without sub being valid
        
        sub_mods = self.reddit.subreddit(sub_name).moderator() # makes list of sub's mods
        banishing_bot = praw.models.Redditor(self.reddit, name='banishing_bot')
        if banishing_bot not in sub_mods: # if not a sub mod before being sent configuration details
            error_checks.append('Insufficient permissions: banishing_bot has not been added as a moderator yet.')
        else: # if bot in sub mods then check perms
            for mod in sub_mods:
                if mod == banishing_bot:
                    for req_perm in reqd_perms:
                        if req_perm not in mod.mod_permissions: # if required perms are not given
                            error_checks.append('Insufficient permissions: banishing_bot has not been given "{}" perms.'.format(req_perm))

        return [config, error_checks]