
"""
Fetches PDFs from the Arxiv, from all categories. 
Borrows heavily from Andrej Kaparthy's Arxiv Sanity Preserver, 
a better tool that can be found here: https://github.com/karpathy/arxiv-sanity-preserver
"""
from nltk.stem.snowball import SnowballStemmer
import process1
import sqlite3
import nltk
import stop_words
import gensim
import urllib
import shutil
import time
import random
import feedparser
import pickle
import os
import re

def encode_feedparser_dict(d):
    """
    *** Directly lifted this from Arxiv Sanity Preserver fetch_paperse.py, by Andrej Kaparthy***
    """
    """ 
     helper function to get rid of feedparser bs with a deep copy. 
     I hate when libs wrap simple things in their own classes.
    """
    if isinstance(d, feedparser.FeedParserDict) or isinstance(d, dict):
        j = {}
        for k in d.keys():
            j[k] = encode_feedparser_dict(d[k])
        return j
    elif isinstance(d, list):
        l = []
        for k in d:
            l.append(encode_feedparser_dict(k))
        return l
    else:
        return d

def process_feed_entry(entry):
    encoded = encode_feedparser_dict(entry)
    url = encoded['id']
    print(url)  
    encoded['shortid'] = url.split('/')[-1]
    return encoded

class Fetcher():
    """
    An object that encapsulates the functions that will fetch the urls and pdfs. 
    """
    
    def __init__(self, connector, number=0, start=0):
        """
        Initializer.
        """
        self.number = number
        self.start = start
        self.c = connector
        self.articles = []

    def fetch_links(self, query='all', care=1):
        """
        Fetches all the links in the given query parameters. 
        """
        base_url = 'http://export.arxiv.org/api/query?'
        categories = 'cat:q-bio+OR+cat:q-fin+OR+cat:math+OR+cat:stat+OR+cat:physics+OR+cat:quant-ph+OR+cat:cs'
        #base_query = 'astro-ph cond-mat gr-qc hep-ex hep-lat hep-ph hep-th math-ph nlin nucl-ex nucl-th physics quant-ph'
        number = 0
        start = self.start
        c = True

        while number < self.number or c == True:
            if self.number == 0 and c == True:
                iters = 25
            else:
                iters = min(self.number - number, 25) 
            end = start + iters + 1
            base_query = 'search_query={0}&sortBy=lastUpdatedDate&start={1}&max_results={2}'.format(categories, start, iters) #Keeping it this way to save energy.
            url = base_url + base_query
            with urllib.request.urlopen(url) as response:
                parsed = feedparser.parse(response)

                if len(parsed.entries) == 0:
                    print("Zero entries retrieved")

                for entry in parsed.entries:
                    entry = process_feed_entry(entry)
                    self.c.execute("""SELECT count(*) FROM articles WHERE arxiv_id=?""", (entry['shortid'],))
                    check = self.c.fetchall()
                    if check == [(0,)]:
                        self.articles.append(entry)
                    elif care == 1:
                        c = False
                        break
                        
                    number += 1

            if number >= self.number and self.number > 0: 
                c = False
            else:
                time.sleep(1.0) ##### Some time
            start = end + 1

    def update_current(self):
        """
        Just some housekeeping stuff
        """
        for article in self.articles():
            self.c.execute("""INSERT INTO current VALUES (?)""", (article['shortid'],))

        self.connection.commit()

    def fetch_pdfs(self):
        """
        This part was lifted from Arxiv Sanity Preserver's download_pdfs.py. Credit to Andrej Kaparthy 
        """
        """
        Fetches the pdfs from the entry links. 
        """

        os.system('mkdir -p pdf') # ?
        os.system('mkdir -p txt') # ?

        timeout_secs = 10 # after this many seconds we give up on a paper
        numok = 0
        numtot = 0
        bad = 0
        have = set(os.listdir('pdf')) # get list of all pdfs we already have
        for entry in self.articles:
            numtot += 1
            print(numtot)
            pdfs = [link['href'] for link in entry['links'] if link['type'] == 'application/pdf']
            print(pdfs)
            assert len(pdfs) == 1
            pdf_url = pdfs[0] + '.pdf'
            basename = pdf_url.split('/')[-1]
            fname = os.path.join('pdf', basename)

            try:
                if not basename in have:
                    print ("fetching %s into %s" % (pdf_url, fname))
                    req = urllib.request.urlopen(pdf_url, None, timeout_secs)
                    with open(fname, 'wb') as fp:
                        shutil.copyfileobj(req, fp)
                    time.sleep(0.1 + random.uniform(0,0.2))
                else:
                    print('%s exists, skipping' % (fname, ))
                numok+=1

            except Exception as e:
                print("error downloading: ", pdf_url)
                print(e)
                if bad == 50:
                    print("Arxiv.org is mad, taking 5 minute nap")
                    time.sleep(300)
                    bad = 0
                bad += 1

        print("%d/%d of %d downloaded ok." % (numok, numtot, len(self.articles)))
        print("final number of papers downloaded okay: %d/%d" % (numok, len(self.articles)))

    def pdf_to_txt(self):
        """
        Runs the linux tool 'pdftotext' to convert all the pdfs into text files, stored in
        the /txt folder.
        """
        for entry in self.articles:
            pdfs = [link['href'] for link in entry['links'] if link['type'] == 'application/pdf']
            pdf_url = pdfs[0] + '.pdf'
            basename = pdf_url.split('/')[-1]
            fname = os.path.join('pdf', basename)
            entry['txtname'] = os.path.join('txt',basename[:-3] + 'txt')
            cmd = 'pdftotext {0} {1}'.format(fname,(entry['txtname']))
            os.system(cmd)

    def tokenize_and_save(self, lda=0):
        """
        For each article in self.articles, get the plaintext, tokenize it, and save everything into 
        the sqlite databse. Thus, memory is somewhat conserved. If the topic model exists, then 
        also create the pesudo_LDA representation.
        """
        have = set(os.listdir('txt'))
        stemmer = SnowballStemmer('english')
        swords = stop_words.get_stop_words('en')
        if lda == 1:
            print("Chose to apply topic model during insert")
            topics = process1.topicModeler
        else:
            print("Not applying topic model during insert")
            topics = []

        for article in self.articles:
            if article['txtname'][4:] in have:
                with open(article['txtname'],'r') as f:
                    print("processing {0}: {1} for tokens and topics".format(article['shortid'], article['title']))
                    text = f.read().lower()
                    tokens = [stemmer.stem(x) for x in nltk.word_tokenize(text) if (not x in swords and re.match('\w',x))]
                    if topics != []:
                        modeled = topics.process_tokens_to_topics(tokens)
                    else:
                        modeled = []

                    print("Inserting into articles table")
                    self.c.execute("""INSERT INTO current VALUES (?)""", (articles['shortid'],))
                    self.c.execute("""INSERT INTO articles 
                        (arxiv_id,date,url,title,abstract,category,author,text,token,topic_rep) 
                        VALUES (?,?,?,?,?,?,?,?,?,?);""", 
                        (article['shortid'], article['published'], article['link'], article['title'],
                        article['summary'],
                        ", ".join([x['term'] for x in article['tags']]),
                        ", ".join([x['name'] for x in article['authors']]),
                        text, " ".join([x for x in tokens]), " ".join(x for x in modeled)))


