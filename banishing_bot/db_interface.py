#TODO: Make config for heroku

import psycopg2
import time
import praw
import os

DATABASE_URL = os.environ['DATABASE_URL']

def receive_configs():
    '''
    INPUT: nothing
    OUTPUT: Config list with the lastest timestamp
    '''
    sql_query = """
    --sql
    SELECT local_config
    FROM local_configs
    ORDER BY created_time desc 
    LIMIT 1
    --endsql
    """
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        cur.execute(sql_query)
        row = cur.fetchone()
        return row[0]
    except(Exception, psycopg2.Error) as e:
        print("Error while working with PostgreSQL:", e)
    finally:
        if conn is not None:
            cur.close()
            conn.close()

def send_configs(time, configs):
    '''
    INPUT: Config list to be sent to db
    OUTPUT: nothing
    '''
    sql_query = """
        --sql
        INSERT INTO local_configs (created_time, local_config)
        VALUES ({}, '{}');
        """
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        cur.execute(sql_query.format(time, configs))
        conn.commit()
    except(Exception, psycopg2.Error) as e:
        print("Error while working with PostgreSQL:", e)
    finally:
        # closes database connection.
        if conn is not None:
            cur.close()
            conn.close()

def send_and_receive_configs(reddit, unread_configs, subreddit_name_param):
    '''
    INPUT: Unread configs to be checked
    OUTPUT: nothing
    '''
    local_configs_str = receive_configs()
    if local_configs_str is not None:
        local_configs = eval(local_configs_str.replace('"', "'")) # gets list from text form in database (substitutes regular single quotes back in)
    else:
        local_configs = []

    if unread_configs:
        for u_config in unread_configs:
            for l_config in local_configs:
                if u_config[subreddit_name_param] == l_config[subreddit_name_param]: # if same sub has sent another config
                    local_configs[local_configs.index(l_config)] = u_config # updates local_config index accordingly
                    unread_configs.remove(u_config) # removes item from unread configs
        for u_config in unread_configs: # for remaining items in unread configs (brand-new configs)
            local_configs.append(u_config) # adds brand-new configs to list of local configs to be sent
    
    banishing_bot = praw.models.Redditor(reddit, name='banishing_bot') # initializes banishing_bot's redditor class
    local_configs = [l_config for l_config in local_configs if banishing_bot in reddit.subreddit(l_config[subreddit_name_param]).moderator()] # removes configs for subs in which bot is not a mod

    send_configs(time.time(), str(local_configs).replace("'", '"')) # sends seconds since the epoch and local configs to be sent (substitutes double quotes for single quotes, for SQL)

    return local_configs