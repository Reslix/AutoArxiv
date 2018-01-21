"""
Fetches links and PDFs from Arxiv.org and stores them in a database using DbConnector.

Most of this is lifted from Andrej Kaparthy's Arxiv Sanity Preserver
https://github.com/karpathy/arxiv-sanity-preserver

"""
import os
import random
import shutil
import time
import urllib

import feedparser

from warden.models import Article, Author, Category, NewArticle


class DataConnector:
    def __init__(self, number=0, start=0):
        self.number = number
        self.start = start
        self.articles = []
        self.mirror_list = ['export', 'lanl', 'es', 'in', 'de', 'cn']

    def encode_feedparser_dict(self, d):
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
                j[k] = self.encode_feedparser_dict(d[k])
            return j
        elif isinstance(d, list):
            l = []
            for k in d:
                l.append(self.encode_feedparser_dict(k))
            return l
        else:
            return d

    def process_feed_entry(self, entry):
        encoded = self.encode_feedparser_dict(entry)
        url = encoded['id']
        print(url)
        encoded['shortid'] = url.split('/')[-1]
        return encoded

    def deserialize_article(self, entry):
        links = [link['href'] for link in entry['links'] if link['type'] == 'application/pdf']
        categories = [Category.objects.get_or_create(name=x['term'])[0] for x in entry['tags']]
        authors = [Author.objects.get_or_create(name=x['name'])[0] for x in entry['authors']]

        article = Article.objects.get_or_create(shortid=entry['shortid'])[0]
        article.set_pdflink(links[0])
        article.set_title(entry['title'])
        article.set_abstract(entry['summary'])
        article.set_date(entry['published'])
        article.set_link(entry['link'])
        article.set_categories(categories)
        article.set_authors(authors)
        article.set_basename(article.pdflink.split('/')[-1][:-4])
        article.set_pdfname(article.basename + '.pdf')
        article.set_txtname(article.basename + '.txt')

        article.save()

        return article

    def fetch_links(self, query='all', care=1, iter_step=100):
        """
        Fetches all the links in the given query parameters.
        """
        base_url = 'http://export.arxiv.org/api/query?'
        categories = 'cat:q-bio.*+OR+cat:q-fin.*+OR+cat:math.*+OR+cat:stat.*+OR+cat:physics.*+OR+cat:quant-ph+OR+cat:cs.*'
        # base_query = 'astro-ph cond-mat gr-qc hep-ex hep-lat hep-ph hep-th math-ph nlin nucl-ex nucl-th physics quant-ph'
        number = 0
        attempts = 0
        small = False
        smaller = False
        smallest = False
        start = self.start
        c = True

        while number < self.number or c is True:
            if self.number == 0 and c is True:
                iters = iter_step
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
                iters = min(self.number - number, iter_step)
            end = start + iters + 1
            if query == 'all':
                base_query = 'search_query={0}&sortBy=lastUpdatedDate&start={1}&max_results={2}'.format(categories,
                                                                                                        start,
                                                                                                        iters)  # Keeping it this way to save energy.
            else:
                base_query = 'id_list={0}&soryBy=lastUpdatedDate&start=0&max_results=1'.format(query)
            url = base_url + base_query
            with urllib.request.urlopen(url) as response:
                parsed = feedparser.parse(response)

                if len(parsed.entries) == 0:
                    print("Zero entries retrieved")
                    end = start - 1
                    if iters == iter_step:
                        small = True
                        attempts += iter_step
                    elif iters == 25:
                        smaller = True
                        attempts += 25
                    elif iters == 5:
                        smallest = True
                        attempts += 5
                    else:
                        attempts += 1

                for entry in parsed.entries:
                    entry = self.process_feed_entry(entry)
                    check = Article.objects.filter(shortid=entry['shortid'])
                    if len(check) == 0:
                        self.articles.append(self.deserialize_article(entry))
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
                time.sleep(0.25)  ##### Some time
            print('Attempts: ', attempts, 'Success: ', number)
            start = end + 1

    def fetch_pdfs(self):
        """
        This part was lifted from Arxiv Sanity Preserver's download_pdfs.py. Credit to Andrej Kaparthy
        """
        """
        Fetches the pdfs from the entry links. 
        """
        cwd = os.getcwd()
        os.system('mkdir -p pdf')  # ?
        os.system('mkdir -p txt')  # ?

        timeout_secs = 10  # after this many seconds we give up on a paper
        numok = 0
        numtot = 0
        mirror_index = 0
        have = set(os.listdir(os.path.join(cwd, 'pdf')))  # get list of all pdfs we already have
        for article in self.articles:
            numtot += 1
            print(numtot)
            mirror_url = (article.pdflink + '.pdf').replace('http://', 'http://' + self.mirror_list[mirror_index] + '.')
            full_pdfpath = os.path.join(cwd, 'pdf', article.pdfname)

            try:
                if not article.pdfname in have:
                    print("fetching %s into %s" % (article.pdflink, full_pdfpath))
                    req = urllib.request.urlopen(mirror_url, None, timeout_secs)
                    with open(full_pdfpath, 'wb') as fp:
                        shutil.copyfileobj(req, fp)
                    time.sleep(0.1 + random.uniform(0, 0.2))
                else:
                    print('%s exists, skipping' % (article.pdfname,))
                numok += 1

            except Exception as e:
                print("Error downloading: ", mirror_url)
                print(e)
                for i in range(len(self.mirror_list) - 1):
                    try:
                        mirror_index = (mirror_index + 1) % len(self.mirror_list)
                        print("Trying again with new mirror")
                        mirror_url = (article.pdflink + '.pdf').replace('http://',
                                                                        'http://' + self.mirror_list[
                                                                            mirror_index] + '.')
                        req = urllib.request.urlopen(mirror_url, None, timeout_secs)
                        with open(full_pdfpath, 'wb') as fp:
                            shutil.copyfileobj(req, fp)
                        time.sleep(0.1 + random.uniform(0, 0.2))
                    except Exception as e:
                        print("Try failed")

        print("%d/%d of %d downloaded ok." % (numok, numtot, len(self.articles)))
        print("final number of papers downloaded okay: %d/%d" % (numok, len(self.articles)))

    def pdf_to_txt(self):
        """
        Runs the linux tool 'pdftotext' to convert all the pdfs into text files, stored in
        the /txt folder.
        """
        cwd = os.getcwd()
        have = set(os.listdir(os.path.join(cwd, 'txt')))
        for article in self.articles:
            full_txtpath = os.path.join(cwd, 'txt', article.txtname)
            full_pdfpath = os.path.join(cwd, 'pdf', article.pdfname)
            if not article.txtname in have:
                print('Converting to text:', article.title)
                cmd = 'pdftotext {0} {1}'.format(full_pdfpath, full_txtpath)
                result = os.system(cmd)
                if str(result).startswith('Syntax'):
                    os.system('rm ' + full_txtpath)
                    print('Removed bad file ', full_txtpath)
            else:
                print('Already have ', article.txtname)

    def save(self, add_new=True):
        """
        For each article in self.articles, get the plaintext, tokenize it, and save everything into
        the sqlite databse. Thus, memory is somewhat conserved. If the topic model exists, then
        also create the pesudo_LDA representation.
        """
        cwd = os.getcwd()
        have = set(os.listdir(os.path.join(cwd, 'txt')))
        for article in self.articles:
            if article.txtname in have:
                with open(os.path.join(cwd, 'txt', article.txtname), 'r') as f:
                    print("Saving: {0}: {1}".format(article.shortid, article.title))
                    text = f.read()
                    article.text = text
                    article.save()
                    if add_new:
                        new_article = NewArticle(article=article)
                        new_article.save()
