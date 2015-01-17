#!/usr/bin/python

from ConfigParser import SafeConfigParser
from itertools import combinations

import os
import urllib

def convert_list(indices):
  return map(int, indices.split(',')) if indices else []

def process_dir(data_path, processed_path, normalise=True):
  config_path = os.path.join(data_path, 'config.ini')
  if not os.path.exists(config_path):
    return

  parser = SafeConfigParser()
  parser.read(config_path)

  dataset_name = parser.get('info', 'name')
  dataset_url = parser.get('info', 'url')
  dataset_class_index = parser.getint('info', 'class_index')
  dataset_id_indices = parser.get('info', 'id_indices')
  dataset_value_indices = parser.get('info', 'value_indices')
  dataset_categoric_indices = parser.get('info', 'categoric_indices')
  dataset_separator = parser.get('info', 'separator')
  dataset_header_lines = parser.getint('info', 'header_lines')

  dataset_id_indices = convert_list(dataset_id_indices)
  dataset_value_indices = convert_list(dataset_value_indices)
  dataset_categoric_indices = convert_list(dataset_categoric_indices)

  dataset_name_orig = '%s.orig' % dataset_name
  dataset_path = os.path.join(data_path, dataset_name_orig)

  # Download the dataset if we don't have it already
  if not os.path.exists(dataset_path):
    urllib.urlretrieve(dataset_url, dataset_path)

  f_in = open(dataset_path, 'rU')

  classes = {}
  class_count = 0

  categoric_classes = [{} for _ in dataset_value_indices]
  categoric_counts = [0 for _ in dataset_value_indices]
  categoric_set = frozenset(dataset_categoric_indices)

  max_val = [-1e10] * len(dataset_value_indices)
  min_val = [1e10] * len(dataset_value_indices)

  row_values = []
  row_classes = []
  row_ids = []

  lines = f_in.readlines()
  lines = lines[dataset_header_lines:]

  for i, line in enumerate(lines):
      if dataset_separator:
          lines[i] = line.strip('\n').split(dataset_separator)
      else:
          lines[i] = line.strip('\n').split()

      row_class = lines[i][dataset_class_index]
      if row_class not in classes:
        classes[row_class] = class_count
        class_count += 1
      row_classes.append(classes[row_class])

      if dataset_id_indices:
          row_ids.append('_'.join([lines[i][j] for j in dataset_id_indices]))
      else:
          row_ids.append('id_%i' % i)

      v = [lines[i][j] for j in dataset_value_indices]

      for j, val in enumerate(v):
          if dataset_value_indices[j] in categoric_set:
              if val not in categoric_classes[j]:
                  categoric_classes[j][val] = categoric_counts[j]
                  categoric_counts[j] += 1
              lines[i][dataset_value_indices[j]] = categoric_classes[j][val]
          else:
              val = float(val)
              if max_val[j] < val:
                  max_val[j] = val
              if min_val[j] > val:
                  min_val[j] = val

  for i, j in enumerate(dataset_value_indices):
      if j in categoric_set:
          max_val[i] = categoric_counts[j] - 1
          min_val[i] = 0

  # Normalise
  if normalise:
      for line in lines:
          values = [line[j] for j in dataset_value_indices]
          row_values.append([str((float(x) - z) / float(y - z))
                             for x, y, z in zip(values, max_val, min_val)])
  else:
      for line in lines:
          row_values.append([line[j] for j in dataset_value_indices])

  f = []
  for i, j in combinations(classes.itervalues(), 2):
      outname = '%s.%s' % (dataset_name, str(i) + '.' + str(j))
      f.append(open(os.path.join(processed_path, outname), 'w'))

  for i, line in enumerate(lines):
      row_class = row_classes[i]
      row_id = row_ids[i]
      out_string = ','.join([row_id] + row_values[i]) + ','

      for i, comb in enumerate(combinations(classes.itervalues(), 2)):
          if row_class in comb:
              row_class_new = 0 if row_class == comb[0] else 1
              f[i].write(out_string + str(row_class_new) + '\n')

  f_in.close()
  for f_out in f:
      f_out.close()

def main(normalise=False):

  root_path = os.path.dirname(__file__)
  datafiles_path = os.path.join(root_path, 'datafiles')

  processed_path = os.path.abspath(os.path.join(root_path, 'processed'))
  if not os.path.exists(processed_path):
    os.makedirs(processed_path)

  for dir in os.listdir(datafiles_path):
    if os.path.isdir(dir):
      continue
    data_path = os.path.join(datafiles_path, dir)
    process_dir(data_path, processed_path, normalise)

if __name__ == '__main__':
  import argparse

  parser = argparse.ArgumentParser(description='Process datafiles.')
  parser.add_argument('-n', '--normalise', action='store_true')

  args = parser.parse_args()
  normalise = args.normalise

  main(normalise)
