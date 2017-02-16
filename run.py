"""
This runs the scripts that fetch, decode, and sort the articles. 
Currently, this runs on a daily cycle.
"""
from datetime import datetime
from relay import Emailer
from fetch import Fetcher
import maintain as m
import argparse
import sqlite3
import time
import sys
"""
Runtime mode:

Fetches new papers. 
RUNS FOREVER
"""
log = open('AutoArxiv.log','a')
old = sys.stdout
sys.stdout = log
c = m.c
f = Fetcher(c)
e = Emailer(c)
#***TODO: add a configuration file
t_count = 0
l_count = 0
fetched = False
trained = False
ldaed = False
updated = False
one_shot = False
fetch_many = False

if fetch_many:
    m.fetch_missing(1000)
    m.update_tfidf()
    m.update_networks()
    m.process_all_users(all=1)
    
if one_shot:
    m.clear_current()
    c.execute('''SELECT arxiv_id from articles ORDER BY date DESC LIMIT 100''')
    a = list(c.fetchall())
    for (i,) in a:
        c.execute_bulk('''INSERT INTO current (arxiv_id) VALUES (?)''', (i,))
    c.commit()

while True:
        now = datetime.now().strftime('%H%M')

        if '2300' <= now <= '2359':
            quit()

        if updated == False:
            print('updating emails')
            e.receive_emails()
            updated = True

        if '0700' <= now <= '0730' and trained == False:
            print("Updating topics and term frequency index...this will take a while")
            try:
                m.update_tfidf()
            except MemoryError:
                pass
            print("Updating all ANN models")
            m.update_networks()
            m.process_all_users(all=1)
            trained = True

        #This part does the new article fetching
        if '0500' <= now <= '0630' and fetched == True:
            fetched = False

        if ('0630' <= now <= '0700' and fetched == False) or one_shot:
            updated = False
            print('Fetching')
            trained = False
            if not (one_shot or fetch_many):
                m.clear_current()
            else:
                one_shot = False
                fetch_many = False
            m.clear_sorted()
            print("Fetching new links...")
            f.fetch_links(itert=100)
            print("Downloading articles...")
            f.fetch_pdfs()
            f.pdf_to_txt()
            print("Storing articles...")
            f.tokenize_and_save()
            #This part will fetch ratings on the new articles. 
            c.execute("""SELECT * FROM current""")
            current = [x for (x,) in list(c.fetchall())]
            print("Updating current word representations")
            m.assign_topics(current)
            print("Sorting new articles")
            m.process_all_users(all=0)
            articles = {}
            for article in current:
                c.execute('''SELECT uid,c_rating FROM sorted WHERE arxiv_id=?''', (article,))
                for user,rating in c.fetchall():
                    c.execute('''SELECT title,url FROM articles WHERE arxiv_id=?''', (article,))
                    title,link = c.fetchall()[0]
                    if not user in articles:
                        articles[user] = [(article, rating, title, link)]
                    else:
                        articles[user].append((article, rating, title, link))

            print("Relaying listings to users")
            for user in articles:
                c.execute('''SELECT email FROM users WHERE uid=?''', (user,))
                email = c.fetchone()[0]
                articles[user].sort(key=lambda x: x[1], reverse=True)
                e.send_listing(email,articles[user])

            fetched = True


        print("Sleeping for 5 minutes")
        time.sleep(300)
sys.stdout = old
log.close()