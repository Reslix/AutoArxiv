"""
This file contains a host of functions to be run for the proper maintenance
of the tool. 

It's just a big bag of things for the time being.

"""
import nltk
import argparse
import sqlite3
from process1 import TopicModeler
from process2 import NeuralModeler
from fetch import Fetcher
import time
dbname = 'auto.sq3'

class DbWrapper():
	"""
	This is an experiment on avoiding annoying database locks.
	"""
	def __init__(self):
		self.connector = sqlite3.connect(dbname)
		self.c = self.connector.cursor()

	def execute(self,statement,tup=None):
		try:
			if tup != None:
				self.c.execute(statement,tup)
			else:
				self.c.execute(statement)
			self.connector.commit()

		except sqlite3.OperationalError:
			print("Database locked, trying again in 3s...")
			time.sleep(3)
			self.execute(statement,tup)
	def rowcount(self):
		return self.c.rowcount
		
	def fetchall(self):
		return self.c.fetchall()

	def fetchone(self):
		return self.c.fetchone()

c = DbWrapper()

def fix_nltk_package():
	nltk.download('punkt')

def fetch_missing(cap=20000):
	"""
	As Arxiv is protective of its bulk data access, it periodically shuts off the 
	valves. Just run this a few times, allotting for breaks, to get things working.
	Run with extreme caution.
	"""
	c.execute('''DELETE FROM articles''')
	f = Fetcher(connector=c)
	f.number = cap
	f.fetch_links(care=0)
	f.fetch_pdfs()
	f.pdf_to_txt()
	f.tokenize_and_save()

def add_user(user,email):
	c.execute('''SELECT name from users''')
	l = list(c.fetchall())
	if not user in l:
		c.execute('''INSERT INTO users (uid,name,email) VALUES (?,?,?)''', (len(l),user,email))
	else:
		print("User name already exists")

def update_user_email(user,email):
	c.execute('''UPDATE users SET email=? WHERE name=?''', (email,user))

def remove_user(user):
	c.execute('''DELETE FROM users WHERE user=?''', (user,))

def remove_article(arxivid):
	c.execute('''DELETE FROM articles WHERE arxiv_id=?''', (arxivid,))

def set_user_ratings(l):
	for arxivid,user,rating in l:
		set_user_rating(arxivid,user,rating)

def set_user_rating(arxivid,user,rating):
	c.execute('''SELECT uid FROM users WHERE email=?''', (user,))
	uid = c.fetchone()[0]
	c.execute('''UPDATE preferences SET c_rating=? WHERE uid=? AND arxiv_id=?''',(rating,uid,arxivid))
	
	if connector.changes() == 0:
		c.execute('''INSERT OR REPLACE preferences (uid,arxiv_id,t_rating,c_rating) 
			VALUES (?,?,(SELECT t_rating FROM preferences 
			WHERE uid=? AND arxiv_id=?),?)''', (uid, arxivid, uid, arxivid, rating))

def clear_current():
	c.execute('''DELETE FROM current''')

def clear_sorted():
	c.execute('''DELETE FROM sorted''')

def update_topics_and_t():
	t = TopicModeler(preload=0, connector=c)
	t.initialize()
	t.create_tfidf_index()
	t.process_all_users()
	t.construct_topic_model()
	t.save_topic_representation()

def update_networks():
	c.execute('''UPDATE preferences SET trained=0''')
	n = NeuralModeler(connector=c)
	n.train_all_users()

def update_user_model(user):
	n = NeuralModeler(connector=c)
	c.execute('''SELECT uid FROM users WHERE user=?''', (user,))
	uid = c.fetchone()[0]
	n.train_user(uid)


def create_tables():
	"""
	Construction mode:

	Creates all the tables in the databse if they do not exist.

	"""
	c.execute('''CREATE TABLE IF NOT EXISTS articles (\
	            arxiv_id TEXT,\
	            date TEXT,\
	            url TEXT, \
	            title TEXT, \
	            abstract TEXT,\
	            category TEXT,\
	            author TEXT,\
	            text TEXT,\
	            token TEXT,\
	            topic_rep TEXT\
	            );\
	            ''')

	c.execute('''CREATE TABLE IF NOT EXISTS users (\
	            uid INTEGER PRIMARY_KEY,\
	            name TEXT,\
	            email TEXT,
	            custom TEXT\
	            );\
	            ''')

	c.execute('''CREATE TABLE IF NOT EXISTS preferences (\
	            uid INTEGER,\
	            arxiv_id TEXT,\
	            t_rating REAL,\
	            c_rating REAL,\
	            trained INTEGER\
	            );\
	            ''')

	c.execute('''CREATE TABLE IF NOT EXISTS sorted (\
	            uid INTEGER,\
	            arxiv_id TEXT,\
	            t_rating REAL,\
	            c_rating REAL\
	            );\
	            ''')

	c.execute('''CREATE TABLE IF NOT EXISTS current (\
	            arxiv_id TEXT\
	            );\
	            ''')
