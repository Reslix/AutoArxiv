from fetch import Fetcher
from process2 import NeuralModeler
from relay import Emailer
import argparse
import maintain as m
import sqlite3
import time
from datetime import datetime
"""
Runtime mode:

Fetches new papers. 
RUNS FOREVER
"""

f = Fetcher()
n = NeuralModeler()
e = Emailer()
c = sqlite3.connect('auto.sq3').cursor()
#***TODO: add a configuration file
t_count = 0
l_count = 0
fetched = False
trained = False
ldaed = False
while True:
      now = datetime.now().strftime('%H%M')

      #This part does the new article fetching
      if '0500' <= now <= '0630' and fetched == False:
            print('fetching')
            t_count += 1
            l_count += 1
            if t_count % 5 == 0:
                  trained = False
            if l_count % 7 == 0:
                  ldaed == 0
            m.clear_current()
            m.clear_sorted()
            print("Fetching new links...")
            f.fetch_links()
            print("Downloading articles...")
            f.fetch_pdfs()
            print("Storing articles...")
            f.tokenize_and_save()

            #This part will fetch ratings on the new articles. 
            c.execute("""SELECT * FROM current""")
            current = zip(*c.fetchall())[0]
            print('sorting new articles')
            n.process_all_users(all=0)
            articles = {}
            for article in current:
                  c.execute("""SELECT uid,rating FROM sorted WHERE arxiv_id=?""", article)
                  for user,rating in c.fetchall():
                        c.execute("""SELECT title,url FROM articles WHERE arxiv_id=?""",article)
                        title,link = c.fetchall()[0]
                        if not user in articles:
                              articles[user] = [(article, rating, title, link)]
                        else:
                              articles[user].append((article, rating, title, link))

            print('relaying listings to users')
            for user in articles:
                  c.execute("""SELECT email FROM users WHERE uid=?""")
                  email = f.fetchone()[0]
                  articles[user].sort(key=lambda x: x[1], descending=True)
                  e.send_listing(email,articles[user])

      if '0400' <= now <= '0430':
            print('updating emails')
            e.recieve_emails()

      if '0630' <= now <= '0640':
            fetched = False

      if '0640' <= now <= '0650' and trained == False:
            print('updating all ANN models')
            n.train_all_users()
            trained = True

      if '0700' <= now <= '0730' and ldaed == False:
            print('updating topics and term frequency index...this will take a while')
            m.update_topics_and_t()
            print('updating all ANN models')
            m.update_network()

      time.sleep(300)
      print('sleeping for 5 minutes')