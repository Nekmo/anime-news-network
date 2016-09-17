from threading import Event

import requests
import time


THREAD_TIMEOUT = 10
URL = 'http://cdn.animenewsnetwork.com/encyclopedia/api.xml'
DELAY = 1


searchs = []
last_search = 0


def is_id(query):
    return isinstance(query, int)


def search(query, type='title'):
    from anime_news_network.results import Results
    wait_to = searchs[-1] if searchs else None
    my_event = Event()
    searchs.append(my_event)
    if wait_to:
        wait_to[-1].wait(THREAD_TIMEOUT)
    if last_search and time.time() - last_search < DELAY:
        time.sleep(max(DELAY - time.time() - last_search, 0))
    query = {type: str(query) if is_id(query) else '~{}'.format(query)}
    data = requests.get(URL, query)
    my_event.set()
    print(Results(data.text).to_json())


search('Haruhi')
