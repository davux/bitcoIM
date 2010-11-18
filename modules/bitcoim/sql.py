# -*- coding: utf-8 -*-
# vi: sts=4 et sw=4

from sqlite3 import connect

class SQL(object):
    '''
    This class makes easy access to the SQL database. Each time you call
    SQL(url) using the same value for url, the same connection is reused.
    If you simply call SQL(), any connection will be used.
    Obviously, you need to provide an URL on the first call at least. If
    you don't, None will be returned.
    '''
    cache = {}

    def __new__(cls, url=None):
        '''The first time a given URL is given, the connection is made and
           stored in a cache. On subsequent calls (with the same URL), it
           will be reused.
           If no URL is given, assume we can use any cached connection (if
           there's no cached connection, return None).
        '''
        if url is None:
            try:
                url = cls.cache.keys()[0]
            except IndexError:
                return None
        if (url not in cls.cache):
            cls.cache[url] = object.__new__(cls)
            cls.cache[url].conn = connect(url, isolation_level=None)
            cls.cache[url].cursor = cls.cache[url].conn.cursor()
            cls.cache[url].execute = cls.cache[url].cursor.execute
            cls.cache[url].commit = cls.cache[url].conn.commit
            cls.cache[url].close = cls.cache[url].conn.close
            cls.cache[url].fetchone = cls.cache[url].cursor.fetchone
            cls.cache[url].fetchall = cls.cache[url].cursor.fetchall
        return cls.cache[url]

    @classmethod
    def close(cls, url=None):
        try:
            if url is None:
                url = cls.cache.keys()[0]
            cls.cache[url].close()
            del cls.cache[url]
        except IndexError:
            pass # No cached connection, or URL not in cache: nothing to close.
