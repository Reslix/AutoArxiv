# AutoArxiv

This is AutoArxiv, a project that I've spent my winter break on. It is meant 
to download articles from Arxiv.org(https://arxiv.org/) and sort them according
to user preference. For the purposes of learning, I decided to incorporate 
LDA topic modeling and a Convolutional Neural Network to see if they can achieve this. 

As I wrote this in a short amount of time, I haven't been able to test out many of the features
or verify that the learning algorithms are doing what I want them to. I also didn't pay too much
attention to proper software development practices, which I intend on rectifying in later versions.

## Setup

First, be sure you have a computer that can handle the computations that will run. In my tests, 
I used a corpus of 3000 articles (that took quite a bit of time). Running the LDA topic model on a 
single core took more than 20 hours and used up a lot of RAM. The CNN model uses the Keras(https://github.com/fchollet/keras/tree/master/keras) framework, which can either use
Theano(http://deeplearning.net/software/theano/) or TensorFlow(https://www.tensorflow.org/), which 
both recommend using CUDA capable graphics processors. 

To setup:
1. Clone the repo.
2. Ensure you are using Python 3. A virtual environment is recommended. Install required modules using `pip install -r requirements.txt`
3. Create directories named 'txt', 'pdf', 'models', 'lda', and 'tfidf'
4. This is where things get messy. Open up the Python3 interpreter and run:
  ```
  import maintain as m    # A hodgepodge file of functions
  m.create_tables()
  
  m.fetch_missing(cap= whatever you feel your article limit is)
  # The above may need to be run a few times to get all the articles down. 
  # Arxiv also may temporarily block you from downloading things
  
  m.update_tfidf_and_t()
  ```
  That last command will take a long time to run, as it performs the LDA training. 
5. At this point, you will need to add a user to the database, which can either be manually done through the sqlite3 command line interface or by running `m.add_user(name,email)`
6. For the time being, updating a user's article ratings is not too straightforward, but it is necessary to have a few preferences before running further training. Determine the article id's (including version) and update the ratings into the 'preferences' table in 'auto.sq3' either manually or by using `m.set_user_rating(arxiv_id,user_email,rating)`. The rating should be between 0 and 100, although that is not checked for. 
7. Now, run `m.update_network`, which should take perhaps an hour or more. 
8. To set up the email system (which is untested), edit `relay.py` and add credentials for a gmail account that
is reserved for this program. 
9. Running `python run.py` from the shell should be all that is left for you to do. If you want to access the ratings for any set of articles outside of the arbitrarily proscribed times used, that will have to be manually achieved for the time being. 


## Acknowledgements 

This project was partly inspired by Andrej Kaparthy's ArxivSanityPreserver(https://github.com/karpathy/arxiv-sanity-preserver), and I owe a lot to CS231n(http://cs231n.stanford.edu/), a course that was vital to my understanding of deep learning. 

This project wouldn't have been possible without my boss, Dr. Charles Tahan(http://www.tahan.com/charlie/), who is the head of the Quantum Computing Group and a Technical Director at the [University of Maryland's Laboratory for Physical Science](http://www.lps.umd.edu/)
