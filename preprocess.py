"""
process1.py performs the Latent Dirilecht Allocation across
all tokenized articles present in the database. There are two stages to this:
the tokens will be vectorized with word2vec and then the LDA algorithm will 
process as it does.

Afterwards, each article will stored in the database.

When reading the APIs, I discovered something called 'skip-grams', which 
look like a promising alternative. They may be implemented in the future
once I get a good idea what their advantages are. 
"""
from gensim import corpora, models, similarities
from random import shuffle
import stop_words
import sqlite3
import gensim
import nltk
import os

class TopicModeler():
    """
    Name is legacy. This class wraps the TFIDF 
    """
    def __init__(self, connector, preload = 0):
        self.plaintext = []
        self.c = connector
        swords = stop_words.get_stop_words('en')
        print("Loading text from db")
        self.c.execute('''SELECT arxiv_id, token FROM articles''')
        self.articles = self.c.fetchall()
        print("Separating text")
        for id,token in self.articles:
             self.plaintext.append((id,token.split()))

        if preload >= 1:
            self.dictionary = corpora.dictionary.Dictionary.load(os.path.join('lda','dictionary'))
        if preload >= 2:   
            print("Assembling corpus from bag")
            self.corpus = [(id, self.dictionary.doc2bow(tokens)) for id, tokens in self.plaintext]
        else:
            self.dictionary = None

    def initialize(self):
        self.dictionary = corpora.dictionary.Dictionary(list(zip(*self.plaintext))[1])
        self.dictionary.save(os.path.join('lda','dictionary'))
        self.corpus = [(id, self.dictionary.doc2bow(tokens)) for id, tokens in self.plaintext]

   
    def load_tfidf(self):
        self.tfidf = models.TfidfModel.load(os.path.join('tfidf','tfidf'))
        self.index = similarities.MatrixSimilarity(self.tfidf[list(zip(*self.corpus))[1]])

    def create_tfidf_index(self):
        print("Creating new tfidf index on articles")
        self.tfidf = models.TfidfModel(list(zip(*self.corpus))[1])
        self.tfidf.save(os.path.join('tfidf','tfidf'))
        self.index = similarities.MatrixSimilarity(self.tfidf[list(zip(*self.corpus))[1]])
        print("Done!")

    def process_user_tscore(self,user):
        """
        Basically, for every user, assign a rating for each article. Entire articles
        will be compared. The conglomerate t_rating will be the average of tfidf rating * the percent
        rating the user assigned.
        """
        print("Processing user tscores for user "+str(user))
        self.c.execute('''SELECT arxiv_id, t_rating, c_rating FROM preferences WHERE uid=?''', (user,))
        articles = self.c.fetchall()
        print("Loaded user preferences")
        ids = list(zip(*self.corpus))[0] 
        temp = {}
        print("Interpolating with main corpus")
        for article in articles:
            temp[article[0]] = article[1],article[2]
        articles = []
        for x in ids:
            if x in temp:
                articles.append((x,temp[x][0],temp[x][1]))
            else:
                articles.append((x,None,None))
        scores = []
        averages = []
        print("Assigning scores") 
        for article in articles:
            if len(articles) == 0:
                print("Should probably assign some preferences...")
            elif article[2] != None:
                print("Assigning..."+article[0])
                self.c.execute('''SELECT token FROM articles WHERE arxiv_id=?''', (article[0],))
                tokens = self.c.fetchone()[0].split()
                minic = self.dictionary.doc2bow(tokens)
                scores.append(self.index[self.tfidf[minic]])

        print("Processing averages")
        dscores = list(zip(*scores))
        for i in range(len(dscores)):
            sum = 0
            for item in dscores[i]:
                sum += item
            averages.append(str(100*sum/len(dscores[i])))

        print(len(ids),len(scores),len(averages))
        for i in range(len(dscores)):
            print("Updating score for user "+str(user)+" and articles "+ids[i]+" to " + str(averages[i]))
            self.c.execute_bulk('''UPDATE preferences SET t_rating=? WHERE uid=? AND arxiv_id=?''', (averages[i],user,ids[i]))
            if self.c.rowcount() == 0:    
                self.c.execute_bulk('''INSERT INTO preferences (uid, arxiv_id, t_rating) 
                    VALUES (?,?,?)''', (user, ids[i], averages[i]))
        self.c.commit()

    def process_all_users(self):
        self.c.execute('''SELECT uid FROM users''')
        users = list(self.c.fetchall())
        for (user,) in users:
            self.c.execute('''SELECT COUNT(*) FROM preferences WHERE uid=?''', (user,))
            count = self.c.fetchall()[0][0]
            self.process_user_tscore(user)

    def save_topic_representation(self,articles=None):
        """
        This used to use LDA until it was dropped without no
        noticable performance detriment.
        """
        self.dictionary.filter_extremes(keep_n=200000)
        self.dictionary.compactify()
        if articles == None:
            articles = self.articles
        self.reverse_dict = {}
        for i in self.dictionary:
            self.reverse_dict[self.dictionary[i]] = i

        for id, tokens in articles:
            ldaed = self.process_tokens_to_topics(tokens)
            print("Updating topic representation of tokens for "+id)
            self.c.execute_bulk('''UPDATE articles SET topic_rep=? WHERE arxiv_id=?;''',
                (' '.join([str(x) for x in ldaed]), id))
        self.c.commit()

    def process_tokens_to_topics(self,tokens):
        id_list = []
        for token in tokens:
            try:
                x = self.reverse_dict[token]
            except KeyError:
                x = -1
            id_list.append(x)

        #topics = self.ldamodel.get_document_topics(id_list,per_word_topics=1)[1]
        #return [x[1][0] if x[1] != [] else -1 for x in topics]
        return id_list

