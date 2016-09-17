import six
from lxml import etree

from anime_news_network.cache import save_title_cache


class ItemBase(object):
    classes = {}
    name = None

    def parse_items(self, items):
        return [self.classes[x.tag](x) if x.tag in self.classes else x for x in items]

    def __repr__(self):
        return '<{}{}>'.format(self.__class__.__name__, ' {}'.format(self.name) if self.name else '')


class Item(dict, ItemBase):
    classes_lists = {}
    set_attributes = True

    def __init__(self, data):
        super(Item, self).__init__()
        self.data = data
        self.set_attribute('class', self.__class__.__name__)
        if self.set_attributes:
            self._set_node_attrs()
        self.set_classes_lists()

    def _set_node_attrs(self):
        for key, value in self.data.attrib.items():
            self.set_attribute(key, value)

    def set_attribute(self, key, value):
        setattr(self, key, value)
        self[key] = value

    def has_attribute(self, key):
        return key in self

    def set_classes_lists(self, items=None):
        items = items or self.parse_items(self.data)
        for item in items:
            if item.__class__ not in self.classes_lists:
                continue
            attr = self.classes_lists[item.__class__]
            if not self.has_attribute(attr):
                self.set_attribute(attr, [])
            self[attr].append(item)

    def to_json(self):
        return self


class News(Item):
    pass


class Staff(Item):
    pass


class Episode(Item):
    pass


class Manganime(Item):
    classes = {'news': News, 'staff': Staff, 'episode': Episode}
    classes_lists = {News: 'news', Staff: 'staff', Episode: 'episodes'}

    def save_cache(self):
        save_title_cache(self.data, self['id'], 'xml')


class Anime(Manganime):
    pass


class Manga(Manganime):
    pass


class Results(list, ItemBase):
    classes = {'anime': Anime, 'manga': Manga}

    def __init__(self, data):
        super(Results, self).__init__()
        if isinstance(data, six.string_types):
            data = etree.fromstring(data)
        self.extend(self.parse_items(data))

    def to_json(self):
        return [obj.to_json() for obj in self]

    def save_cache(self):
        for item in self:
            item.save_cache()
