
"""
Fetches PDFs from the Arxiv, from all categories. 
Borrows heavily from Andrej Kaparthy's Arxiv Sanity Preserver, 
a better tool that can be found here: https://github.com/karpathy/arxiv-sanity-preserver

TODO: Have link fetching be 
"""
from nltk.stem.snowball import SnowballStemmer
import feedparser
import stop_words
import sqlite3
import gensim
import pickle
import random
import shutil
import urllib
import nltk
import time
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
        self.mirror_list = ['export','lanl','es','in','de','cn']

    def fetch_links(self, query='all', care=1, itert=100):
        """
        Fetches all the links in the given query parameters. 
        """
        base_url = 'http://export.arxiv.org/api/query?'
        categories = 'cat:q-bio.*+OR+cat:q-fin.*+OR+cat:math.*+OR+cat:stat.*+OR+cat:physics.*+OR+cat:quant-ph+OR+cat:cs.*'
        #base_query = 'astro-ph cond-mat gr-qc hep-ex hep-lat hep-ph hep-th math-ph nlin nucl-ex nucl-th physics quant-ph'
        number = 0
        attempts = 0
        small = False
        smaller = False
        smallest = False
        start = self.start
        c = True

        while number < self.number or c == True:
            if self.number == 0 and c == True:
                iters = itert
            elif small:
                iters = 25
                small = False
            elif smaller:
                iters = 5
                smaller = False
                small = True
            elif smallest:
                iters = 1
                smallest = False
                smaller = True
            else:
                iters = min(self.number - number, itert) 
            end = start + iters + 1
            base_query = 'search_query={0}&sortBy=lastUpdatedDate&start={1}&max_results={2}'.format(categories, start, iters) #Keeping it this way to save energy.
            url = base_url + base_query
            with urllib.request.urlopen(url) as response:
                parsed = feedparser.parse(response)

                if len(parsed.entries) == 0:
                    print("Zero entries retrieved")
                    end = start - 1
                    if iters == itert:
                        small = True
                        attempts += itert
                    elif iters == 25:
                        smaller = True
                        attempts += 25
                    elif iters == 5:
                        smallest = True
                        attempts += 5
                    else:    
                        attempts += 1
                
                for entry in parsed.entries:
                    entry = process_feed_entry(entry)
                    self.c.execute("""SELECT count(*) FROM articles WHERE arxiv_id=?""", (entry['shortid'],))
                    check = self.c.fetchall()
                    if check == [(0,)]:
                        self.articles.append(entry)
                    elif care == 1:
                        print("Entry exists")
                        c = False
                        break
                    else:
                        print("Entry exists")
                    number += 1
                    attempts += 1

            if number >= self.number and self.number > 0: 
                c = False
            else:
                time.sleep(0.25) ##### Some time
            print('Attempts: ',attempts,'Success: ',number)
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
        mirror_index = 0
        have = set(os.listdir('pdf')) # get list of all pdfs we already have
        for entry in self.articles:
            numtot += 1
            print(numtot)
            pdfs = [link['href'] for link in entry['links'] if link['type'] == 'application/pdf']
            print(pdfs)
            assert len(pdfs) == 1
            pdf_url = (pdfs[0] + '.pdf').replace('http://','http://' + self.mirror_list[mirror_index] +'.')
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
                print("Error downloading: ", pdf_url)
                print(e)
                for i in range(len(self.mirror_list)-1):
                    try:
                        mirror_index = (mirror_index + 1) % len(self.mirror_list)
                        print("Trying again with new mirror")
                        pdf_url = (pdfs[0] + '.pdf').replace('http://','http://' + self.mirror_list[mirror_index] +'.')
                        req = urllib.request.urlopen(pdf_url, None, timeout_secs)
                        with open(fname, 'wb') as fp:
                            shutil.copyfileobj(req, fp)
                        time.sleep(0.1 + random.uniform(0,0.2))
                    except Exception as e:
                        print("Try failed")

        print("%d/%d of %d downloaded ok." % (numok, numtot, len(self.articles)))
        print("final number of papers downloaded okay: %d/%d" % (numok, len(self.articles)))

    def pdf_to_txt(self):
        """
        Runs the linux tool 'pdftotext' to convert all the pdfs into text files, stored in
        the /txt folder.
        """
        have = set(os.listdir('txt'))
        for entry in self.articles:
            pdfs = [link['href'] for link in entry['links'] if link['type'] == 'application/pdf']
            pdf_url = pdfs[0] + '.pdf'
            basename = pdf_url.split('/')[-1]
            fname = os.path.join('pdf', basename)
            entry['txtname'] = os.path.join('txt',basename[:-3] + 'txt')
            if not basename[:-3] + 'txt' in have:
                print('Converting',fname)
                cmd = 'pdftotext {0} {1}'.format(fname,(entry['txtname']))
                result = os.system(cmd)
                if str(result).startswith('Syntax'):
                    os.system('rm '+fname)
                    print('Removed bad file ',fname)
            else:
                print('Already have ', basename[:-3] + 'txt')

    def tokenize_and_save(self, lda=0):
        """
        For each article in self.articles, get the plaintext, tokenize it, and save everything into 
        the sqlite databse. Thus, memory is somewhat conserved. If the topic model exists, then 
        also create the pesudo_LDA representation.
        """
        have = set(os.listdir('txt'))
        stemmer = SnowballStemmer('english')
        swords = stop_words.get_stop_words('en')
        
        for article in self.articles:
            if article['txtname'][4:] in have:
                with open(article['txtname'],'r') as f:
                    print("processing {0}: {1}".format(article['shortid'], article['title']))
                    text = f.read().lower()
                    tokens = [stemmer.stem(x) for x in nltk.word_tokenize(text) if (re.match('\w',x))]
                    self.c.execute_bulk('''SELECT COUNT(*) FROM articles WHERE arxiv_id=?''', (article['shortid'],))
                    if self.c.fetchall() == [(0,)]:
                        self.c.execute_bulk("""INSERT INTO current VALUES (?)""", (article['shortid'],))
                        self.c.execute_bulk("""INSERT INTO articles 
                            (arxiv_id,date,url,title,abstract,category,author,text,token) 
                            VALUES (?,?,?,?,?,?,?,?,?);""", 
                            (article['shortid'], article['published'], article['link'], article['title'],
                            article['summary'],
                            ", ".join([x['term'] for x in article['tags']]),
                            ", ".join([x['name'] for x in article['authors']]),
                            text, " ".join([x for x in tokens])))
        self.c.commit()


