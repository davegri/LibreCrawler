from Crawler import Crawler
import os
import datetime
import time
import requests
from distance import hamming
from blockhash import blockhash
from config import DB, THUMBNAIL_DIR

photos = DB.photos


class MongoCrawler(Crawler):
    def __init__(self, short_name, long_name, base_url, domain, nested_scrape=False):
        Crawler.__init__(self, base_url, domain, nested_scrape=nested_scrape)
        self.short_name = short_name
        self.long_name = long_name

    def image_exists(self, image_page_url):
        return photos.find({'sources': { '$elemMatch': {'pageURL':image_page_url} } } ).count() > 0

    def save_thumbnail(self, thumb, image_url):
        img_name = os.path.basename(image_url.split('?', 1)[0])
        file_path = os.path.join(THUMBNAIL_DIR, img_name)
        thumb.save(file_path, 'JPEG')
        return file_path

    def duplicate_exists(self, hash):
        cursor = photos.find()
        for photo in cursor:
            if hamming(hash, photo['hash']) < 5:
                return photo
        return None

    def store_image(self, image_source_url, image_page_url, image_thumbnail_url, tags):
        thumb = self.create_thumbnail(image_thumbnail_url)
        file_path = self.save_thumbnail(thumb, image_thumbnail_url)

        hash = blockhash(thumb, 256)
        duplicate = self.duplicate_exists(hash)

        source = {
            'short_name': self.short_name,
            'long_name': self.long_name,
            'URL': image_source_url,
            'pageURL': image_page_url,
        }

        if duplicate is not None:
            id = duplicate['_id']
            print('Found duplicate, id: {}.\n adding tags and new source'.format(id))
            photos.update_one({'_id': id}, {'$addToSet': {'tags':tags, 'sources':source}})
            return

        image = {
            'thumbnail': file_path,
            'sources': [source],
            'tags': tags,
            'hash': hash,
            'creationDate': datetime.datetime.now(),
        }
        photos.insert_one(image)
