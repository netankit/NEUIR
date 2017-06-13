from print_tweets import *

def expand_query(session,holder,input_value,dataset, similarity, word_batch_dict, top_k):
    tweet_list = top_tweets(top_k)
    print(tweet_list)
    word_batch_list = []
    for tweet in tweet_list:
        word_batch_list += list(word_batch_dict[tweet])
    feed_dict = { holder : input_value }
    sim = session.run(similarity, feed_dict=feed_dict)
    l = (-sim).argsort()
    nearest = filter(lambda x: x in word_batch_list and x != 0,l)
    print(nearest[:20])
    return nearest