*** TODO: Improve documentation, fix some sketchy things going on in here ***


AutoArxiv will return a daily email listing of new articles, ordered
by relevance to a user's reading preferences. It will use an algorithm 
that uses a regression convnet with Latent Dirilecht Allocation input. 

The intution behind this is that 

The first step is to get articles from Arxiv. This will be done in the "fetch" 
class, which will extract from the Arxiv API articles using the "urllib" and
"feedparser" modules. The link information will be stored in a SQLite database. 
then, the articles will be downloaded and stored in a PDF folder. concurrently, 
the articles will be converted into plaintext and stored in the same
SQLite database. 

Once there is a sizable corpus, of probably 4000+ articles from all of 
Arxiv, in a representative sample, LDA will be performed in order to 
create a large number of topics. For now, there will be 1000 topics. 
This number will be optimized in the future, of course. To achieve this, 
a tokenized version of the plaintext needs to be constructed, which removes
punctuation, stopwords, and numerical figures. This will be done with 
the "nltk" or "gensim", depending on ease of use. 

With the returned topics, the articles can be sorted. 

In order for the sorting to occur, there need to be users. A default test user
will be created with a selection 20 articles in a computer science category. The
number will be dependent on the minimal articles needed to train an accurate network.

Besides the neural network implementation, there will be a simple tf-idf correlation 
of topics. This will be one of the parameters.  

The network application that will be used is the Microsoft CNTL

The current model that will be used is a five layer convolutional neural network. 
The input will be an article, or perhaps its abstract, so a length of 20000 in 
one dimension, and then the size of the topics (1024). Stopwords, figures, punctuation
and etc are to be ignored under the assumption that such details ultimately matter
less than content figures. 

As topic models represent probability distributions of how words fit in topics, 
the highest probability category for the word given. 

In normal operation, the AutoArxiv will download new articles at a set time 
every day and run the users' networks. A list of relevant articles above the 50 percent
threshold will be sent via email to the users. 

The "run.py" file will do the following:
	1. Have a construction mode, which downloads the corpus and runs all the initial processing. 
	2. Have a normal runtime mode, which fetches and sorts new papers either daily or when prompted. 
		The test user will not have emails sent, but rather a debug output only. 
	3. Will run the "fetch" file in mode 2,3,4
	4. Will run the "process2" file for every user.

The "maintain.py" file will do the following:
	1. Add and remove users
	2. Add and remove articles for users and their ratings. 
	3. Ensure that users will not get previously selected files. 

The "fetch.py" file will do the following:
	1. Fetch articles to a numerical amount, by category. 
	2. Fetch new articles, as in until an existing article is met. 
	3. Fetch the pdfs of the articles and convert them to text. 
	4. Tokenize the plaintext and keep track of the top 19 stopwords. 

The "process1.py" file will do the following:
	1. Perform LDA for 1000 topics on the existing corpus 
	2. Convert tokenized text into a vectorized LDA representation


The "process2.py" file will do the following:
	1. Given a user, train a convnet specifically for that user based on 
		available regression training data.
		a. If an article is trained upon and the predicted rating has also
			been used, then don't use it. 
		b. If an article is trained upon but the predicted rating is not
			current, then use it. 
		c. Otherwise, train on the preferences. 
		*** Only the top some number of articles will be trained, according to 
			tf-idf. This will reduce
	2. Given a set of ArxivId's and user, evaluate the user's predicted
		preference. 
	3. Store newly sorted articles in Current after clearing it. 

The "relay.py" file will do the following: 
	1. Given a non-empty Current table, for non test users, 
		collect them and generate a string with hyperlinks to be sent via email
		to the users. 
	2. For test users, give out the debug output. 
	3. Recieve emails from users, which depending on subject line, 
		adds and removes articles and user ratings to the database, returns a user's libary, or
		a sorted listing.

The "dbwrapper.py" file will do the following:
	1. Interact with the database using "sqlite3" in a more conveninent manner
	2. Be able to add and remove rows to tables
	3. Be able to retrieve rows from tables with filered queries.
 
The general schema for the databases will go as follows:

Articles:
	Arxiv_ID Date URL Abstract Category Author Plaintext Tokenized Topic_rep.

Users:
	UID Name email custom

Preferences:
	UID ArxivID t_rating c_rating trained?

#The trained? flag for Preferences highlights whether or not
the user specified rating has been changed since the last convnet run. 

Sorted:
	UID ArxivID t_rating c_rating 

Current:
	ArxvID

The topic model will be stored in however the module used sees fit. 