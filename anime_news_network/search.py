from threading import Event

import requests
import time

from anime_news_network.cache import load_title_cache, save_word_cache, load_word_cache
from anime_news_network.results import Results
from lxml import etree

THREAD_TIMEOUT = 10
URL = 'http://cdn.animenewsnetwork.com/encyclopedia/api.xml'
DELAY = 1
LABELS = ['anime', 'manga', 'title']
LABEL_IDS = 'title'

searchs = []
last_search = 0


def is_id(query):
    return isinstance(query, int)


def _search_cache(query, type):
    if is_id(query):
        results = load_title_cache(query, ext='xml')
    else:
        results = load_word_cache(query, type)
    if results is None:
        return
    if is_id(query):
        results = [results]
    else:
        results = [int(x) for x in results.split(',')]
        results = [load_title_cache(result, ext='xml') for result in results]
    ann = etree.Element('ann')
    for result in results:
        ann.append(result)
    return Results(ann)


def search(query, label='title'):
    if is_id(query):
        label = LABEL_IDS
    results = _search_cache(query, label)
    if results is None:
        results = _search_request(query, label)
    print(results.to_json())


def _search_request(query, label):
    from anime_news_network.results import Results
    # Última petición en espera
    wait_to = searchs[-1] if searchs else None
    my_event = Event()
    # Pongo el Event (semáforo) a la lista para que las siguientes sepan que existe
    searchs.append(my_event)
    if wait_to:
        # Si hay una petición ya en curso, espero a que termine
        wait_to[-1].wait(THREAD_TIMEOUT)
    # Tengo que espera DELAY entre búsqueda y búsqueda
    if last_search and time.time() - last_search < DELAY:
        time.sleep(max(DELAY - time.time() - last_search, 0))
    query_search = {label: str(query) if is_id(query) else '~{}'.format(query)}
    data = requests.get(URL, query_search)
    # Libero para que otros puedan hacen consultas
    my_event.set()
    searchs.remove(my_event)
    results = Results(data.text)
    # Guardo los titles (es decir, las fichas)
    results.save_cache()
    if not is_id(query):
        # Si es una búsqueda por palabras,
        save_word_cache(query, label, [result.id for result in results])
    return results
