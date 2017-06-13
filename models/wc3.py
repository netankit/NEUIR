from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import operator
import collections
import math
import time
import os
import random
import zipfile
import time
import numpy as np
import sys
from six.moves import urllib
from six.moves import xrange  # pylint: disable=redefined-builtin
import tensorflow as tf
sys.path.append( '../util/')
from generators import *
from loader import *
from print_tweets import *
from similar_tokens import * 
from training import *
from similar_tokens import *
from expand_query import *

args = sys.argv
dataset = args[1]
query_type = int(args[2])
if len(args) >= 4:
    args[0] = args[3]
# Read the data into a list of strings.
# import data
word_batch_dict,data, count, dictionary, reverse_dictionary, word_max_len, char_max_len, vocabulary_size, char_dictionary, reverse_char_dictionary, data_index, char_data_index, buffer_index, batch_list, char_batch_list, word_batch_list, char_data = build_everything(dataset)
# Step 3: Function to generate a training batch for the skip-gram model.


data_index, batch, labels = generate_batch(data, data_index, batch_size=8, num_skips=2, skip_window=1,)
for i in range(8):
  print(batch[i], reverse_dictionary[batch[i]],
        '->', labels[i, 0], reverse_dictionary[labels[i, 0]])
char_data_index, batch, labels = generate_batch_char(char_data, char_data_index, batch_size=8, num_skips=2, skip_window=1)
for i in range(8):
  print(batch[i], reverse_char_dictionary[batch[i]],
        '->', labels[i, 0], reverse_char_dictionary[labels[i, 0]])

# Step 4: Build and train a skip-gram model.

batch_size = 128
embedding_size = 128  # Dimension of the embedding vector.
skip_window = 2       # How many words to consider left and right.
num_skips = 2         # How many times to reuse an input to generate a label.
skip_char_window = 2
num_char_skips = 3
char_vocabulary_size = len(char_dictionary)
print(char_vocabulary_size)
# We pick a random validation set to sample nearest neighbors. Here we limit the
# validation samples to the words that have a low numeric ID, which by
# construction are also the most frequent.
valid_size = list()
valid_window = list()
valid_size.append(16)     # Random set of words to evaluate similarity on.
valid_size.append(10)
valid_window.append(100)  # Only pick dev samples in the head of the distribution.
valid_window.append(20)
valid_examples = []
valid_examples.append(np.random.choice(valid_window[0], valid_size[0], replace=False))
valid_examples.append(np.random.choice(valid_window[1], valid_size[1], replace=False))
valid_examples[0][0] = dictionary['nee']
valid_examples[0][1] = dictionary['avail']
num_sampled = 64    # Number of negative examples to sample.
char_batch_size = 128
if query_type == 1:
  query_tokens = map(lambda x: dictionary[x],['nee','requir'])
elif query_type == 2:
  query_tokens = map(lambda x: dictionary[x],['send','distribut','avail'])
tweet_batch_size = 128
lambda_1 = 0.7

graph = tf.Graph()
learning_rate = 5e-1

with graph.as_default():

  # Input data.
  train_inputs = tf.placeholder(tf.int32, shape=[batch_size])
  train_input_chars = tf.placeholder(tf.int32, shape=[char_batch_size])
  train_labels = tf.placeholder(tf.int32, shape=[batch_size, 1])
  train_char_labels = tf.placeholder(tf.int32, shape=[char_batch_size, 1])
  word_char_embeddings = tf.placeholder(tf.int32, shape=[batch_size, char_max_len])
  valid_dataset = tf.constant(valid_examples[0], dtype=tf.int32)
  valid_char_dataset = tf.constant(valid_examples[1], dtype=tf.int32)
  query_ints = tf.placeholder(tf.int32, shape=len(query_tokens))
  expanded_query_ints = tf.placeholder(tf.int32, shape=(len(query_tokens)+3))
  # Ops and variables pinned to the CPU because of missing GPU implementation
  tweet_char_holder = tf.placeholder(tf.int32, shape=[tweet_batch_size,word_max_len,char_max_len])
  tweet_word_holder = tf.placeholder(tf.int32, shape=[tweet_batch_size, word_max_len])
  with tf.device('/cpu:0'):
    # Look up embeddings for inputs.
    embeddings = tf.Variable(tf.random_uniform([vocabulary_size, embedding_size], -1.0, 1.0))
    char_embeddings = tf.Variable(tf.random_uniform([char_vocabulary_size, embedding_size],-1.0,1.0))
    embed = tf.nn.embedding_lookup(embeddings, train_inputs)
    char_embed = tf.nn.embedding_lookup(char_embeddings,train_input_chars)
    lambda_2 = tf.Variable(tf.random_normal([1],stddev=1.0))

    # Construct the variables for the NCE loss
    nce_weights = tf.Variable(
        tf.truncated_normal([vocabulary_size, embedding_size],
                            stddev=1.0 / math.sqrt(embedding_size)))
    nce_biases = tf.Variable(tf.zeros([vocabulary_size]))
    # character weights
    nce_char_weights = tf.Variable(
        tf.truncated_normal([vocabulary_size, embedding_size],
                            stddev=1.0 / math.sqrt(embedding_size)))
    nce_char_biases = tf.Variable(tf.zeros([vocabulary_size]))

    nce_train_weights = tf.Variable(
        tf.truncated_normal([vocabulary_size, embedding_size],
                            stddev=1.0 / math.sqrt(embedding_size)))
    nce_train_biases = tf.Variable(tf.zeros([vocabulary_size]))
    
  loss = tf.reduce_mean(
      tf.nn.nce_loss(weights=nce_weights,
                     biases=nce_biases,
                     labels=train_labels,
                     inputs=embed,
                     num_sampled=num_sampled,
                     num_classes=vocabulary_size))

  loss_char = tf.reduce_mean(
      tf.nn.nce_loss(weights=nce_char_weights,
                     biases=nce_char_biases,
                     labels=train_char_labels,
                     inputs=char_embed,
                     num_sampled=10,
                     num_classes=char_vocabulary_size))

  # Construct the SGD optimizer using a learning rate of 1.0.
  optimizer = tf.train.GradientDescentOptimizer(learning_rate).minimize(loss)
  optimizer_char = tf.train.AdamOptimizer(learning_rate /5).minimize(loss_char)

  # Compute the cosine similarity between minibatch examples and all embeddings.
  norm = tf.sqrt(tf.reduce_sum(tf.square(embeddings), 1, keep_dims=True))
  normalized_embeddings = embeddings / norm
  valid_embeddings = tf.nn.embedding_lookup(
      normalized_embeddings, valid_dataset)
  similarity = tf.matmul(
      valid_embeddings, normalized_embeddings, transpose_b=True)
  query_embedding_token = tf.reshape(tf.reduce_mean(tf.nn.embedding_lookup(normalized_embeddings,query_ints),axis=0),shape=[1,embedding_size])
  expanded_query_embedding_token = tf.reshape(tf.reduce_mean(tf.nn.embedding_lookup(normalized_embeddings,expanded_query_ints),axis=0),shape=[1,embedding_size])
  similarity_query = tf.reshape(tf.matmul(
      query_embedding_token, normalized_embeddings, transpose_b=True),shape=[int(normalized_embeddings.shape[0])])
  similarity_expanded_query = tf.reshape(tf.matmul(
      expanded_query_embedding_token, normalized_embeddings, transpose_b=True),shape=[int(normalized_embeddings.shape[0])])

  norm_char = tf.sqrt(tf.reduce_sum(tf.square(char_embeddings), 1, keep_dims=True))
  normalized_char_embeddings = char_embeddings / norm_char
  valid_embeddings_char = tf.nn.embedding_lookup(
      normalized_char_embeddings, valid_char_dataset)
  similarity_char = tf.matmul(
      valid_embeddings_char, normalized_char_embeddings, transpose_b=True)
  
  character_word_embeddings = tf.nn.embedding_lookup(normalized_char_embeddings, word_char_embeddings)
  with tf.variable_scope("lstm"):
    lstm = tf.contrib.rnn.BasicLSTMCell(embedding_size//2,reuse=tf.get_variable_scope().reuse)
  revlstm = tf.contrib.rnn.BasicLSTMCell(embedding_size//2,reuse=tf.get_variable_scope().reuse)
  output_fwd = []
  output_bwd = []
  state_fwd = lstm.zero_state(batch_size, dtype=tf.float32)
  state_bwd = revlstm.zero_state(batch_size, dtype=tf.float32)
  for l in range(char_max_len):
    if l > 0: 
      with tf.variable_scope(tf.get_variable_scope(),reuse=True):
        with tf.variable_scope("lstm"):
          cell_output_fwd, state_fwd = lstm(character_word_embeddings[:,l],state_fwd)
        cell_output_bwd, state_bwd = revlstm(character_word_embeddings[:,l],state_bwd)
        cell_output_fwd = tf.reshape(cell_output_fwd, shape=[batch_size,1,embedding_size//2])
        cell_output_bwd = tf.reshape(cell_output_bwd, shape=[batch_size,1,embedding_size//2])
        output_fwd = tf.concat([output_fwd, cell_output_fwd],axis=1)
        output_bwd = tf.concat([cell_output_bwd, output_bwd],axis=1)
    else:
      with tf.variable_scope("lstm"):
        cell_output_fwd, state_fwd = lstm(character_word_embeddings[:,l],state_fwd)
      cell_output_bwd, state_bwd = revlstm(character_word_embeddings[:,l],state_bwd)
      output_fwd = tf.reshape(cell_output_fwd, shape=[batch_size,1,embedding_size//2])
      output_bwd = tf.reshape(cell_output_bwd, shape=[batch_size,1,embedding_size//2])

  intermediate = tf.concat([output_bwd, output_fwd],axis=2)
  attention = tf.nn.softmax(tf.matmul(vvector, tf.nn.tanh(tf.matmul(intermediate,weights)),transpose_a=True))
  output = tf.reshape(tf.matmul(attention,intermediate),shape=[batch_size,embedding_size])

  word_embeddings = tf.nn.embedding_lookup(normalized_embeddings, train_inputs)
  final_embedding = lambda_2*word_embeddings + (1-lambda_2)*output
  with tf.variable_scope(tf.get_variable_scope(), reuse=None):

    loss_char_train = tf.reduce_mean(
      tf.nn.nce_loss(weights=nce_train_weights,
                     biases=nce_train_biases,
                     labels=train_labels,
                     inputs=final_embedding,
                     num_sampled=64,
                     num_classes=vocabulary_size))

    optimizer_train = tf.train.AdamOptimizer(learning_rate/5).minimize(loss_char_train)

  tweet_word_embed = tf.nn.embedding_lookup(normalized_embeddings, tweet_word_holder)
  tweet_char_embeddings = tf.reshape(tf.nn.embedding_lookup(normalized_char_embeddings, tweet_char_holder),shape=[tweet_batch_size*word_max_len, char_max_len, embedding_size//2])
  output_fwd = []
  output_bwd = []
  state_fwd = lstm.zero_state(tweet_batch_size*word_max_len, dtype=tf.float32)
  state_bwd = revlstm.zero_state(tweet_batch_size*word_max_len, dtype=tf.float32)
  for l in range(char_max_len):
    with tf.variable_scope(tf.get_variable_scope(),reuse=True):
      with tf.variable_scope("lstm"):
        cell_output_fwd, state_fwd = lstm(tweet_char_embeddings[:,l],state_fwd)
      cell_output_bwd, state_bwd = revlstm(tweet_char_embeddings[:,l],state_bwd)
    if l == 0: 
      output_fwd = tf.reshape(cell_output_fwd, shape=[tweet_batch_size*word_max_len,1,embedding_size//2])
      output_bwd = tf.reshape(cell_output_bwd, shape=[tweet_batch_size*word_max_len,1,embedding_size//2])
    else:
      with tf.variable_scope("lstm"):
        cell_output_fwd = tf.reshape(cell_output_fwd, shape=[tweet_batch_size*word_max_len,1,embedding_size//2])
      cell_output_bwd = tf.reshape(cell_output_bwd, shape=[tweet_batch_size*word_max_len,1,embedding_size//2])
      output_fwd = tf.concat([output_fwd, cell_output_fwd],axis=1)
      output_bwd = tf.concat([cell_output_bwd, output_bwd],axis=1)

  intermediate = tf.concat([output_bwd, output_fwd],axis=2)
  attention = tf.nn.softmax(tf.matmul(vvector_tweet, tf.nn.tanh(tf.matmul(intermediate,weights_tweet)),transpose_a=True))
  tweet_char_embed = tf.reshape(tf.matmul(attention,intermediate),shape=[tweet_batch_size,word_max_len,embedding_size])
  tweet_embedding = tf.reduce_mean(lambda_1*tweet_word_embed + (1-lambda_1)*tweet_char_embed,axis=1)
  query_embedding = tf.reshape(tf.reduce_mean(tf.nn.embedding_lookup(normalized_embeddings,query_ints),axis=0),shape=[1,embedding_size])
  expanded_query_embedding = tf.reshape(tf.reduce_mean(tf.nn.embedding_lookup(normalized_embeddings,expanded_query_ints),axis=0),shape=[1,embedding_size])
  query_similarity = tf.reshape(tf.matmul(tweet_embedding, query_embedding, transpose_b=True),shape=[tweet_batch_size])
  expanded_query_similarity = tf.reshape(tf.matmul(tweet_embedding, expanded_query_embedding, transpose_b=True),shape=[tweet_batch_size])
  # Add variable initializer.
  init = tf.global_variables_initializer()
  saver = tf.train.Saver()

# Step 5: Begin training.
num_steps = 200001
num_steps_roll = 200001
num_steps_train = 600001
# loading tweet list in integer marking form
# load more data
expand_count = 3
with tf.Session(graph=graph) as session:
  # We must initialize all variables before we use them.
  init.run()
  count = 0
  print("Initialized")

  generators = [generate_batch, generate_batch_char]
  similarities = [similarity, similarity_char]
  placeholders = [[train_inputs,train_labels],[train_input_chars,train_char_labels]]
  losses = [loss, loss_char]
  optimizers = [optimizer, optimizer_char]
  interval1 = 2000
  interval2 = 10000
  datas = [data,char_data]
  data_index = [data_index, char_data_index, buffer_index]
  reverse_dictionaries = [reverse_dictionary, reverse_char_dictionary]
  if query_type == 1:
    query_name = 'Need'
  elif query_type == 2:
    query_name == 'Avail'
  print(query_tokens)
  train_model(session, dataset,query_similarity, query_tokens, query_ints, query_name, word_batch_list, char_batch_list, tweet_word_holder, tweet_char_holder, generators, similarities, num_steps, placeholders,losses, optimizers, interval1, interval2, valid_size, valid_examples, reverse_dictionaries, batch_size, num_skips, skip_window, args[0], datas, data_index, tweet_batch_size)
  placeholders += [[train_inputs, word_char_embeddings, train_labels]]
  losses += [loss_char_train]
  optimizers += [optimizer_train]
  datas += [[word_batch_list, char_batch_list]]
  train_model(session, dataset,query_similarity, query_tokens ,query_ints, query_name, word_batch_list, char_batch_list, tweet_word_holder, tweet_char_holder, generators, similarities, num_steps_roll, placeholders,losses, optimizers, interval1, interval2, valid_size, valid_examples, reverse_dictionaries, batch_size, num_skips, skip_window, args[0], datas, data_index, tweet_batch_size)
  expanded_query_tokens = query_tokens + expand_query(session,query_ints, np.array(query_tokens),dataset ,similarity_query, word_batch_dict, 100)[2:2+expand_count]
  print(expanded_query_tokens)
  train_model(session, dataset,expanded_query_similarity, expanded_query_tokens, expanded_query_ints, query_name, word_batch_list, char_batch_list, tweet_word_holder, tweet_char_holder, generators, similarities, num_steps_train , placeholders,losses, optimizers, interval1, interval2, valid_size, valid_examples, reverse_dictionaries, batch_size, num_skips, skip_window, args[0], datas, data_index, tweet_batch_size)
  folder_name = './%s/%s/'%(dataset, query_type)
  final_embeddings = normalized_embeddings.eval()
  final_char_embedding = normalized_char_embeddings.eval()
  np.save('%sword_embeddings.npy', final_embeddings)
  np.save('%schar_embeddings.npy', final_char_embedding)