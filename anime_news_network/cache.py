import csv
import datetime
import hashlib
import os

import json
import six
from lxml import etree

CACHE_DIR = os.path.expanduser('~/.local/cache')
WORDS_CACHE_DIR = os.path.join(CACHE_DIR, 'words')
TITLES_CACHE_DIR = os.path.join(CACHE_DIR, 'titles')
WORDS_CSV_FIELDS = ['name', 'label', 'titles', 'updated_at']
WORDS_CSV_DIALECT = 'excel-tab'

def makedirs(path, mode=0o777, exist_ok=False):
    if exist_ok and os.path.exists(path):
        return
    os.makedirs(path, mode)


makedirs(CACHE_DIR, exist_ok=True)
makedirs(WORDS_CACHE_DIR, exist_ok=True)
makedirs(TITLES_CACHE_DIR, exist_ok=True)


def get_title_cache_path(name, ext='json'):
    return os.path.join(TITLES_CACHE_DIR, '.'.join([name, ext]))


def get_word_cache_path(name):
    hash = hashlib.md5(name.encode('utf-8')).hexdigest()[:2]
    return os.path.join(WORDS_CACHE_DIR, '{}.csv'.format(hash))


def save_title_cache(data, name, ext='json'):
    file = get_title_cache_path(name, ext)
    if not isinstance(data, six.string_types) and ext == 'json':
        data = json.dumps(data)
    elif not isinstance(data, six.string_types) and ext == 'xml':
        data = etree.tostring(data)
        data = data.decode('utf-8')
    with open(file, 'w') as f:
        f.write(data)


def load_title_cache(name, ext='json'):
    name = str(name)
    file = get_title_cache_path(name, ext)
    if not os.path.lexists(file):
        return
    if ext == 'json':
        return json.load(open(file))
    elif ext == 'xml':
        return etree.fromstring(open(file).read())
    else:
        return open(file).read()


def _get_csv_reader(name):
    return csv.DictReader(open(get_word_cache_path(name)), fieldnames=WORDS_CSV_FIELDS, dialect=WORDS_CSV_DIALECT)


def _save_word_cache(path, lines):
    f = open(path, 'w')
    d = csv.DictWriter(f, fieldnames=WORDS_CSV_FIELDS, dialect=WORDS_CSV_DIALECT)
    d.writerows(lines)
    f.close()


def _create_word_cache_line(name, label, titles):
    return {'name': name, 'label': label, 'titles': titles, 'updated_at': datetime.datetime.now().isoformat()}


def save_word_cache(name, label, titles):
    titles = ','.join([str(title) for title in titles])
    path = get_word_cache_path(name)
    lines = list(_get_csv_reader(name)) if os.path.lexists(path) else []
    new_line = _create_word_cache_line(name, label, titles)
    for i, line in enumerate(lines):
        if not line['name'] == name and line['label'] == label:
            continue
        lines[i] = new_line
        return _save_word_cache(path, lines)
    lines.append(new_line)
    _save_word_cache(path, lines)


def load_word_cache(name, label):
    path = get_word_cache_path(name)
    lines = list(_get_csv_reader(name)) if os.path.lexists(path) else []
    for line in lines:
        if line['name'] == name and line['label'] == label:
            return line['titles']
