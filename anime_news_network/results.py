import datetime
import re

import dateutil
import dateutil.parser
import six
from lxml import etree

from anime_news_network.cache import save_title_cache
from anime_news_network.utils import parse_date, safe_compare


def match_dict(target, match):
    for key, value in target.items():
        if match.get(key) != value:
            return False
    return True


class ItemBase(object):
    tag_classes = {}
    tag_attr_classes = []
    name = None

    def parse_item(self, x):
        for tag_attr, class_ in self.tag_attr_classes:
            if tag_attr[0] == x.tag and match_dict(tag_attr[1], x.attrib):
                return class_(x)
        return self.tag_classes[x.tag](x) if x.tag in self.tag_classes else x

    def parse_items(self, items):
        return [self.parse_item(x) for x in items]

    def __repr__(self):
        return '<{}{}>'.format(self.__class__.__name__, ' {}'.format(self.name) if self.name else '')


class Item(dict, ItemBase):
    classes_lists = {}
    classes_attrs = {}
    attrs_content = []
    set_attributes = True
    content = None
    url_base = None

    def __init__(self, data):
        super(Item, self).__init__()
        self.data = data
        self.set_attribute('class', self.__class__.__name__)
        if self.set_attributes:
            self._set_node_attrs()
        self._set_classes_lists()
        self._set_classes_attrs()
        self._set_attrs_content()
        self.set_content()
        self._set_url()
        self._parse_attributes()
        self.post_init()

    def post_init(self):
        pass

    def _set_url(self):
        if not self.url_base:
            return
        self.set_attribute('url', self.url_base.format(**self.to_json()))

    def _set_node_attrs(self):
        for key, value in self.data.attrib.items():
            self.set_attribute(key, value)

    def set_attribute(self, key, value):
        setattr(self, key, value)
        self[key] = value

    def has_attribute(self, key):
        return key in self

    def set_content(self):
        if self.content:
            self.set_attribute(self.content, self.data.text)

    def _parse_attributes(self):
        starts_with = '_parse_'
        for name in dir(self):
            if not name.startswith(starts_with) or name == '_parse_attributes':
                continue
            method = getattr(self, name)
            value = method()
            if value is None:
                continue
            self.set_attribute(name.replace(starts_with, '', 1), value)

    def _set_classes_lists(self, items=None):
        items = items or self.parse_items(self.data)
        for item in items:
            if item.__class__ not in self.classes_lists:
                continue
            attr = self.classes_lists[item.__class__]
            if not self.has_attribute(attr):
                self.set_attribute(attr, [])
            self[attr].append(item)

    def _set_classes_attrs(self, items=None):
        items = items or self.parse_items(self.data)
        for item in items:
            if item.__class__ not in self.classes_attrs:
                continue
            attr = self.classes_attrs[item.__class__]
            self.set_attribute(attr, item)

    def _set_attrs_content(self):
        for obj in self.attrs_content:
            xpath = ''
            xpath = xpath + (obj['tag'] if 'tag' in obj else '')
            xpath = xpath + (''.join(["[@{}='{}']".format(key, value) for key, value in obj['attrs'].items()])
                             if 'attrs' in obj else '')
            element = self.data.find(xpath)
            if element is not None:
                self.set_attribute(obj['name'], obj['function'](element.text) if 'function' in obj else element.text)

    def _parse_id(self, attr='id'):
        try:
            return int(self[attr]) if attr in self else None
        except ValueError:
            return float(self[attr]) if attr in self else None

    def _parse_gid(self):
        return self._parse_id('gid')

    def _parse_date(self):
        date = self.get('date')
        return parse_date(date) if date else None

    def _parse_datetime(self):
        dt = self.get('datetime')
        if not dt:
            return
        return dateutil.parser.parse(dt)

    def to_json(self):
        return self


class Title(Item):
    content = 'name'


class ItemTitles(Item):
    tag_classes = {'title': Title}
    classes_lists = {Title: 'titles'}


class Person(Item):
    content = 'name'
    url_base = 'http://www.animenewsnetwork.com/encyclopedia/people.php?id={id}'


class Company(Item):
    content = 'name'
    url_base = 'http://www.animenewsnetwork.com/encyclopedia/company.php?id={id}'

class TaskItem(Item):
    tag_classes = {'person': Person, 'company': Company}
    classes_lists = {Person: 'people', Company: 'companies'}
    attrs_content = [
        {'name': 'task_name', 'tag': 'task'},
        {'name': 'person_name', 'tag': 'person'},
        {'name': 'company_name', 'tag': 'company'},
        {'name': 'role_name', 'tag': 'role'},
    ]


class News(Item):
    content = 'name'


class Staff(TaskItem):
    pass


class Episode(ItemTitles):
    def _parse_num(self):
        return self._parse_id('num')


class Credit(TaskItem):
    pass


class Cast(TaskItem):
    pass


class Opening(ItemTitles):
    pass


class Ending(ItemTitles):
    pass


class Release(Item):
    pass


class MainTitle(Item):
    pass


class AlternativeTitle(Item):
    pass


class Genre(Item):
    content = 'name'
    url_base = 'http://www.animenewsnetwork.com/encyclopedia/search/genreresults?g={name}&o=rating'


class Theme(Item):
    content = 'name'
    url_base = 'http://www.animenewsnetwork.com/encyclopedia/search/genreresults?g={name}&o=rating'


class OfficialWebsite(Item):
    content = 'name'


class Rating(Item):
    def _parse_nb_votes(self):
        return int(self.get('nb_votes', 0))

    def _parse_bayesian_score(self):
        return float(self.get('bayesian_score', 0))

    def _parse_weighted_score(self):
        return float(self.get('weighted_score', 0))


class PremiereDate(Item):
    content = 'description'

    def post_init(self):
        description = self.get('description')
        if description and ' ' in description:
            date, market = description.split(' ', 1)
            self.set_attribute('market', market[1:][:-1])
            self.set_attribute('date', parse_date(date))


class Img(Item):
    pass


class Pictures(list, ItemBase):
    def __init__(self, data):
        super(Pictures, self).__init__()
        self.data = data
        for img in self.data:
            self.append(Img(img))


class RelatedPrev(Item):
    pass


class RelatedNext(Item):
    pass


class Vintage(Item):
    content = 'description'

    def post_init(self):
        dates = re.findall('[0-9]{4}\-[0-9]{2}\-[0-9]{2}', self['description'])
        serialized = re.findall('serialized in (.+?)\)', self['description'])
        self.set_attribute('release_date', dates[0]) if len(dates) > 0 else None
        self.set_attribute('completed_date', dates[1]) if len(dates) > 1 else None
        self.set_attribute('serialized', serialized[0]) if len(serialized) > 0 else None


class Manganime(Item):
    # xml element tag: class
    tag_classes = {
        'news': News, 'staff': Staff, 'episode': Episode, 'credit': Credit, 'cast': Cast, 'release': Release,
        'ratings': Rating, 'related-prev': RelatedPrev
    }
    tag_attr_classes = [
        (('info', {'type': 'Opening Theme'}), Opening),
        (('info', {'type': 'Alternative title'}), AlternativeTitle),
        (('info', {'type': 'Main title'}), MainTitle),
        (('info', {'type': 'Genres'}), Genre),
        (('info', {'type': 'Themes'}), Theme),
        (('info', {'type': 'Official website'}), OfficialWebsite),
        (('info', {'type': 'Picture'}), Pictures),
        (('info', {'type': 'Premiere date'}), PremiereDate),
        (('info', {'type': 'Vintage'}), Vintage),
    ]
    attrs_content = [
        {'name': 'number_of_episodes', 'tag': 'info', 'attrs': {'type': 'Number of episodes'}, 'function': int},
        {'name': 'plot_summary', 'tag': 'info', 'attrs': {'type': 'Plot Summary'}},
        {'name': 'objectionable_content', 'tag': 'info', 'attrs': {'type': 'Objectionable content'}},
    ]

    # class: attribute list
    classes_lists = {
        News: 'news', Staff: 'staff', Episode: 'episodes', Credit: 'credits', Cast: 'cast',
        Opening: 'openings', Release: 'releases', AlternativeTitle: 'alternative_titles',
        Genre: 'genres', Theme: 'themes', PremiereDate: 'vintages', Vintage: 'vintages',
    }
    classes_attrs = {
        MainTitle: 'main_title', Rating: 'rating', Pictures: 'pictures', RelatedPrev: 'related_prev',
        RelatedNext: 'related_next'
    }

    def _related(self, name):
        obj = self.get('related_{}'.format(name))
        if obj is not None:
            from anime_news_network.search import search
            return search(obj.id)[0]

    def next(self):
        return self._related('next')

    def prev(self):
        return self._related('prev')

    def post_init(self):
        if self.get('vintages') and 'release_date' in self['vintages'][0]:
            self.set_attribute('release_date', self['vintages'][0]['release_date'])

    def save_cache(self):
        save_title_cache(self.data, self['id'], 'xml')


class Anime(Manganime):
    url_base = 'http://www.animenewsnetwork.com/encyclopedia/anime.php?id={id}'


class Manga(Manganime):
    url_base = 'http://www.animenewsnetwork.com/encyclopedia/manga.php?id={id}'


class Results(list, ItemBase):
    tag_classes = {'anime': Anime, 'manga': Manga}

    def __init__(self, data):
        super(Results, self).__init__()
        if isinstance(data, six.string_types):
            data = etree.fromstring(data)
        if isinstance(data, list):
            self.extend(data)
        else:
            self.extend(self.parse_items(data))

    def to_json(self):
        return [obj.to_json() for obj in self]

    def save_cache(self):
        for item in self:
            item.save_cache()

    def sort_by(self, key):
        return Results(sorted([x for x in self], key=safe_compare(lambda x: x.get(key))))
