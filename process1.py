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
from gensim.models.ldamulticore import LdaModel
from gensim import corpora, models, similarities
import sqlite3
import gensim
import os
import nltk
import stop_words


class TopicModeler():
    """
    This class wraps a topic modeling feature that vectorizes text tokens
    and then creates a topic model using LDA. There will be 1024 topic categories. 
    """
    def __init__(self, preload = 0):
        self.plaintext = []
        self.connector = sqlite3.connect('auto.sq3')
        self.c = self.connector.cursor()
        swords = stop_words.get_stop_words('en')
        print("Loading text from db")
        self.c.execute("""SELECT arxiv_id, text, token FROM articles""")
        self.articles = self.c.fetchall()
        print("Tokenizing text")
        for id,text,token in self.articles:
             self.plaintext.append((id,token.split()))

        if preload == 1:
            self.ldamodel = LdaModel.load(os.path.join('lda','lda'))
            self.dictionary = corpora.dictionary.Dictionary.load(os.path.join('lda','dictionary'))
            print("Assembling corpus from bag")
            self.corpus = [(id, self.dictionary.doc2bow(tokens)) for id, tokens in self.plaintext]
        else:
            self.ldamodel = None
            self.dictionary = None

    def initialize(self):
        self.dictionary = corpora.dictionary.Dictionary(list(zip(*self.plaintext))[1])
        self.dictionary.save(os.path.join('lda','dictionary'))
        self.corpus = [(id, self.dictionary.doc2bow(tokens)) for id, tokens in self.plaintext]

    def construct_topic_model(self):
        """
        Constructs a topic model based on tokenized and stopword proceeded 

        """
        #Ultimately, we want to leave one topic open as there may be words that don't exist.
        self.ldamodel = LdaModel(list(zip(*self.corpus))[1], num_topics=1023, id2word = self.dictionary, passes=7)
        self.ldamodel.save(os.path.join('lda','lda'))

    def load_tfidf(self):
        self.tfidf = models.TfidfModel.load(os.path.join('tfidf','tfidf'))
        self.index = similarities.MatrixSimilarity(self.tfidf[list(zip(*self.corpus))[1]])

    def create_tfidf_index(self):
        self.tfidf = models.TfidfModel(list(zip(*self.corpus))[1])
        self.tfidf.save(os.path.join('tfidf','tfidf'))
        self.index = similarities.MatrixSimilarity(self.tfidf[list(zip(*self.corpus))[1]])

    def process_user_tscore(self,user):
        """
        Basically, for every user, assign a rating for each article. Entire articles
        will be compared. The conglomerate t_rating will be the average of tfidf rating * the percent
        rating the user assigned.
        """
        print("Processing user tscores")
        self.c.execute("""SELECT arxiv_id, t_rating, c_rating FROM preferences WHERE uid=?""", (user,))
        articles = self.c.fetchall()
        print("Loaded user preferences")
        ids = list(zip(*self.corpus))[0]  #This is going for a very questionable index matching
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
                self.c.execute("""SELECT token FROM articles WHERE arxiv_id=?""", (article[0],))
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
            self.c.execute("""UPDATE preferences SET t_rating=? WHERE uid=? AND arxiv_id=?""", (averages[i],user,ids[i]))
            self.connector.commit()
            if self.connector.changes() == 0:
                self.c.execute("""INSERT OR REPLACE INTO preferences (uid, arxiv_id, t_rating, c_rating) 
                    VALUES (?,?,?,(SELECT c_rating FROM preferences WHERE uid=? AND arxiv_id=?))""",
                    (user, ids[i], averages[i], user, ids[i]))
                self.connector.commit()

    def process_all_users(self):
        self.c.execute("""SELECT uid FROM users""")
        users = list(self.c.fetchall())
        for user in users:
            self.process_user_tscore(user[0])

    def save_topic_representation(self):
        self.reverse_dict = {}
        for i in self.dictionary:
            self.reverse_dict[self.dictionary[i]] = i

        for id, tokens in self.plaintext:
            ldaed = self.process_tokens_to_topics(tokens)
            print(ldaed)
            self.c.execute("""UPDATE articles SET topic_rep=? WHERE arxiv_id=?;""",
                (" ".join([str(x) for x in ldaed]), id))
            self.connector.commit()

    def process_tokens_to_topics(self,tokens):
        id_list = []
        for token in tokens:
            try:
                x = self.reverse_dict[token]
            except KeyError:
                x = -1
            id_list.append((x,1))

        topics = self.ldamodel.get_document_topics(id_list,per_word_topics=1)[1]

        return [x[1][0] if x[1] != [] else -1 for x in topics]
