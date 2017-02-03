"""
Here lies the convnet model that will try to make sense of things. 
Unfortuantely, I'm not sure if the network is interacting with the input
the way I'm envisioning. Changes are sure to come here. 

#The module that will be used is Microsofts CNTK, which I am experimenting with.

The modlue that will be used is Keras/Theano. Although it does not have the performance
desired, it has the features required. Future versions will attempt to transition
to another framework once I am more familiar with deep learning. Fortunately,
it appears that CNTK is attempting to follow keras' model of organization.

"""
#from __future__ import print_function
#from cntk.device import set_default_device, gpu
#from cntk.learner import adagrad, UnitType
#from cntk.ops.functions import load_model, relu,
#from cntk import Trainer
#import cntk as C
from keras.layers.convolutional import Convolution2D, Convolution1D
from keras.layers import Dense, Embedding, Flatten, Reshape
from keras.preprocessing.sequence import pad_sequences
from keras.models import load_model
from keras.models import Sequential
from keras import backend as K
from random import shuffle
import numpy as np
import sqlite3
import os

K.set_image_dim_ordering('th')

class NeuralModeler():
    """
    This class encapsulates all the functions revolving around the convnet.
    """
    def __init__(self, connector):
        """
        Sets up a sqlite wrapper for some I/O operations.
        """
        self.c = connector
        self.articles = None
        self.model = None
        self.master_dict = None

    def create_user_model_base(self, user):
        """
        Creates a new convnet file for a new user. The current plan is for each user
        to have their own network, although that may turn out to be impractical.
        For future updates, will explore the idea of having just one network give out
        all the regressions and have users be a separate parameter at the input layer.

        Given the speed of training and processing, this article
        """
        model = Sequential()
        #Used to be 1024, now 2000001
        model.add(Embedding(2000001, 128, input_length=10000))
        model.add(Reshape((1, 20000, 128)))
        model.add(Convolution2D(nb_filter=64, nb_col=128, nb_row=5, activation='relu'))
        model.add(Convolution2D(nb_filter=32, nb_col=1, nb_row=5, activation='relu'))
        model.add(Convolution2D(nb_filter=32, nb_col=1, nb_row=5, activation='relu'))
        model.add(Convolution2D(nb_filter=32, nb_col=1, nb_row=5, activation='relu'))
        model.add(Flatten())
        model.add(Dense(128))
        model.add(Dense(1))
        model.compile('adagrad', loss='mean_squared_error', metrics=['accuracy'])

        model.save(os.path.join('models', str(user)+'_nolda'))

    def save_model(self, user):
        """
        Stores the sequential model.
        """
        self.model.save(os.path.join('models', str(user)+'_nolda'))

    def load_model(self, user):
        """
        Loads an already trained model.
        """
        self.model = load_model(os.path.join('models', str(user)+'_nolda'))

    def train_current_model(self, debug=1):
        """
        Trains a loaded model.
        """
        arxiv_id, abstract, topic_rep, ratings = zip(*self.articles)
        for t,r in zip(topic_rep, ratings):
            print(t,r)
            self.model.fit(np.array(t).reshape(1,20000), np.array([r]), verbose=debug)

    def train_user(self, uid):
        """
        This prepares the training data for each user. Each word representation
        is split by spaces and truncated to a 10000 feature limit padded by -1's.

        The topic_rep format of the articles is already mostly formatted into what we need.
        """
        self.c.execute("""SELECT arxiv_id,t_rating,c_rating FROM preferences WHERE uid=?""", (uid,))
        preferences = list(self.c.fetchall())
        shuffle(preferences)
        self.articles = []
        randoms = []
        selected = []
        for entry in preferences:
            print(entry)
            self.c.execute("""SELECT arxiv_id, abstract, topic_rep FROM articles WHERE arxiv_id=?""", (entry[0],))
            result = list(self.c.fetchall())
            if len(result) > 0:
                result = result[0]
                padded = pad_sequences([[int(x) for x in result[2].split()]], maxlen=10000, value=-1, padding='post', truncating='post')
                if entry[2] != None:
                    result = (result[0], result[1], padded[0], entry[2])
                    for i in range(4):
                        selected.append(result)
                else:
                    result = (result[0], result[1], padded[0], entry[1])
                    randoms.append(result)

        shuffle(randoms)
        self.articles.extend(selected)
        self.articles.extend(randoms[:2000])
        shuffle(self.articles)
        self.train_current_model()

    def train_all_users(self):
        """
        Trains all users listed in the users table
        """
        have = set(os.listdir('models'))
        self.c.execute("""SELECT uid FROM users""")
        users = list(self.c.fetchall())
        for user in users:
            if not user in have: 
                self.create_user_model_base(str(user[0]))
            self.load_model(str(user[0]))
            self.train_user(str(user[0]))
            self.save_model(str(user[0]))

    def process_user(self, user, save=True, debug=0, all=0):
        """
        This will run the prediction algorithm on all articles that haven't been trained
        for the particular user. This will either run on all articles in the database,
        or only articles in the 'current' table, which lists newly fetched articles.
        """
        print("Feeding articles into user model for user " + str(user))
        results = []
        self.load_model(user)
        if self.master_dict == None:
            self.c.execute("""SELECT arxiv_id,title,topic_rep FROM articles""")
            master_list = list(self.c.fetchall())
            self.master_dict = {}
            while master_list != []:
                entry  = master_list.pop()
                self.master_dict[entry[0]] = entry[1], entry[2]
                
        if all == 1:
            articles = self.master_dict.keys()
        else:
            self.c.execute('''SELECT * FROM current''')
            articles = [x for (x,) in self.c.fetchall()]

        for article in articles:
            topics = [int(x) for x in self.master_dict[article][1].split()]
            topics = pad_sequences([topics], maxlen=10000, value=-1, padding='post', truncating='post')
            rating = self.model.predict(np.array(topics), verbose=debug)
            print(article, self.master_dict[article][0], rating)
            results.append((article, rating))
            self.c.execute_bulk('''UPDATE sorted SET c_rating=? WHERE uid=? AND arxiv_id=?''',(int(rating[0][0]), int(user), article))
            if self.c.rowcount() == 0:
                self.c.execute_bulk('''INSERT INTO sorted (uid,arxiv_id,c_rating) 
                    VALUES (?,?,?)''', (int(user), article, int(rating[0][0])))
        self.c.commit()
      

    def process_all_users(self, save=True, debug=1, all=0):
        """
        Predicts article ratings for all users in the users table.
        """
        self.c.execute('''SELECT uid FROM users''')
        users = list(self.c.fetchall())
        for user in users:
            self.process_user(str(user[0]), save, debug, all)
