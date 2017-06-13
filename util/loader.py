import collections
import numpy as  np
def read_data(filename):
  """Extract the first file enclosed in a zip file as a list of words"""
  with open(filename,mode="r") as f:
    data = f.read()
    data_chars = list(set(data))
  return data.split(),data_chars,data

# Step 2: Build the dictionary and replace rare words with UNK token.


def build_dataset(words, vocabulary_size,dataset):
  count = [['UNK', -1]]
  count.extend(collections.Counter(words).most_common(vocabulary_size - 1))
  dictionary = dict()
  for word, _ in count:
    dictionary[word] = len(dictionary)
  data = list()
  unk_count = 0
  for word in words:
    if word in dictionary:
      index = dictionary[word]
    else:
      index = 0  # dictionary['UNK']
      unk_count += 1
    data.append(index)
  count[0][1] = unk_count
  reverse_dictionary = dict(zip(dictionary.values(), dictionary.keys()))
  return data, count, dictionary, reverse_dictionary

def build_everything(dataset):
  vocabulary_size = 50000
  with open("../data/%s/data.npy"%(dataset)) as fil:
    t = fil.readlines()
  word_max_len, char_max_len = map(lambda x: int(x),t)

  filename = '../data/%s/corpus.txt'%(dataset)
  words,chars,character_data = read_data(filename)
  print('Data size', len(words))

  char_dictionary = dict()
  for char in chars:
    char_dictionary[char] = len(char_dictionary)

  reverse_char_dictionary = dict(zip(char_dictionary.values(),char_dictionary.keys()))
  char_data = []
  for char in character_data:
    char_data.append(char_dictionary[char])

  data, count, dictionary, reverse_dictionary = build_dataset(words, vocabulary_size, dataset)
  del words  # Hint to reduce memory.
  print('Most common words (+UNK)', count[:5])
  print('Sample data', data[:10], [reverse_dictionary[i] for i in data[:10]])

  data_index = 0
  char_data_index = 0

  word_batch_list = np.load("../data/%s/word_embedding.npy"%(dataset))
  char_batch_list = np.load("../data/%s/char_embedding.npy"%(dataset))
  with open("../data/%s/tweet_ids.txt"%(dataset)) as fil:
    tweet_list = map(lambda y: filter(lambda x: x != '\n',y), fil.readlines())
  word_batch_dict = dict(zip(tweet_list, word_batch_list))
  batch_list = dict()
  buffer_index = 1
  return word_batch_dict,data, count, dictionary, reverse_dictionary, word_max_len, char_max_len, vocabulary_size, char_dictionary, reverse_char_dictionary, data_index, char_data_index, buffer_index, batch_list, char_batch_list, word_batch_list, char_data
