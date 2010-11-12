# -*- coding: utf-8 -*-
# vi: sts=4 et sw=4

from sqlite import connect
from conf import db

class SQL(object):
    cache = None

    def __new__(cls):
        if cls.cache is None:
            cls.cache = object.__new__(cls)
            cls.cache.conn = connect(db['file'])
            cls.cache.cursor = cls.cache.conn.cursor()
            cls.cache.execute = cls.cache.cursor.execute
            cls.cache.commit = cls.cache.conn.commit
            cls.cache.close = cls.cache.conn.close
            cls.cache.fetchone = cls.cache.cursor.fetchone
            cls.cache.fetchall = cls.cache.cursor.fetchall
        return cls.cache

    @classmethod
    def close(cls):
        if cls.cache is not None:
            cls.cache.close()
            cls.cache = None
