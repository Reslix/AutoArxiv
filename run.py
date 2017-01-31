"""
This runs the scripts that fetch, decode, and sort the articles. 
Currently, this runs on a daily cycle.
"""
from process2 import NeuralModeler
from datetime import datetime
from relay import Emailer
from fetch import Fetcher
import maintain as m
import argparse
import sqlite3
import time
"""
Runtime mode:

Fetches new papers. 
RUNS FOREVER
"""

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
c.execute('''SELECT COUNT(*) FROM articles''')
if c.fetchall() == [(0,)]:
    m.process_all_users(all=1)
while True:
    
        now = datetime.now().strftime('%H%M')

        #This part does the new article fetching
        if '0500' <= now <= '0630':
            fetched = False

        if '0630' <= now and fetched == False:
            updated = False
            print('Fetching')
            t_count += 1
            l_count += 1
            trained = False
            if l_count % 7 == 0:
                ldaed == 0
            m.clear_current()
            m.clear_sorted()
            print("Fetching new links...")
            f.fetch_links(iter=5)
            print("Downloading articles...")
            f.fetch_pdfs()
            f.pdf_to_txt()
            print("Storing articles...")
            f.tokenize_and_save()

            #This part will fetch ratings on the new articles. 
            c.execute("""SELECT * FROM current""")
            current = list(c.fetchall())
            print("Sorting new articles")
            m.process_all_users(all=0)
            articles = {}
            for (article,) in current:
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

        if '0400' <= now <= '0430' and updated == False:
            print('updating emails')
            e.receive_emails()
            updated = True

        if '0100' <= now <= '0200' and trained == False and ldaed == True:
            print("Updating all ANN models")
            n.train_all_users()
            trained = True

        if '0000' <= now <= '0100' and ldaed == False:
            print("Updating topics and term frequency index...this will take a while")
            m.update_topics_and_t()
            print("Updating all ANN models")
            m.update_network()

        print("Sleeping for 5 minutes")
        time.sleep(300)
