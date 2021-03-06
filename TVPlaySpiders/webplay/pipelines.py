# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from datetime import datetime
from hashlib import md5
import logging
from scrapy.exceptions import DropItem
from twisted.enterprise import adbapi
from webplay.items import *

class WebplayPipeline(object):
    def process_item(self, item, spider):
        return item
        
class MySqlPipeline(object):
    """A pipeline to store the item in a MySQL database.
    This implementation uses Twisted's asynchronous database API.
    """
    def __init__(self, dbpool):
        self.dbpool = dbpool
    
    @classmethod
    def from_settings(cls, settings):
        dbargs = dict(
            host=settings['MYSQL_HOST'],
            db=settings['MYSQL_DBNAME'],
            user=settings['MYSQL_USER'],
            passwd=settings['MYSQL_PASSWD'],
            charset='utf8',
            use_unicode=True,
            cp_reconnect = True,
        )
        dbpool = adbapi.ConnectionPool('pymysql', **dbargs)
        return cls(dbpool)
        
    def process_item(self,item,spider):
        # run db query in the thread pool
        d = self.dbpool.runInteraction(self._do_upsert, item, spider)
        d.addErrback(self._handle_error, item, spider)
        # at the end return the item in case of success or failure
        d.addBoth(lambda _: item)
        # return the deferred instead the item. This makes the engine to
        # process next item (according to CONCURRENT_ITEMS setting) after this
        # operation (deferred) has finished.
        return d

    def _do_upsert(self, conn, item, spider): 
        """Perform an insert or update."""
        guid = self._get_guid(item)
        item.setdefault('additional_infos', {})
        item.setdefault('area', None)
        item.setdefault('desc', None)
        item.setdefault('episodes', None)
        item.setdefault('directors', None)
        item.setdefault('actors', None)
        item.setdefault('cover_img', None)
        item.setdefault('cover_img_sm', None)
        item.setdefault('playStatus', None)
        item.setdefault('genre', None)
        item.setdefault('tags', None)
        item.setdefault('lastepisode', None)
        item.setdefault('releaseDate', None)
        item.setdefault('alias', None)
        item.setdefault('renqi', None)
        item.setdefault('playCount', None)
        conn.execute("""INSERT IGNORE into `tbl_tvplay_rawdata` 
        (`url`,`aid`,`guid`,`name`,`area`,
        `desc`,`episodes`,`directors`,`actors`,
        `cover_img_sm`,`cover_img`,`playDate`,
        `playCount`,`playStatus`,`genre`,`tags`,
        `lastepisode`,`additional_infos`,`website`,
        `releaseDate`,`alias`,`renqi`)
        values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);""", 
        (item['url'],item['aid'],guid,item['name'],
        item['area'],item['desc'],item['episodes'],
        item['directors'],item['actors'],item['cover_img_sm'],
        item['cover_img'],item['playdate'],item['playCount'],
        item['playStatus'],item['genre'],item['tags'],
        item['lastepisode'],str(item['additional_infos']),
        item['website'],item['releaseDate'],item['alias'],item['renqi']))
        logging.info("Item updated in db: %s %r" % (guid, item))

    def _handle_error(self, failure, item, spider):
        """Handle occurred on db interaction."""
        # do nothing, just log
        logging.error(item['url'])
        logging.error(failure)

    def _get_guid(self, item):
        """Generates an unique identifier for a given item."""
        # hash based solely in the url field
        try:
            return md5(item['url']).hexdigest()
        except:
            return md5(item['url'].encode('utf8')).hexdigest()
