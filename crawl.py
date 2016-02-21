from MongoCrawler import MongoCrawler

import logging
logger = logging.getLogger('LibreCrawler')
from clint.arguments import Args

# Initialize coloredlogs.
import coloredlogs
logFormat = '%(asctime)s %(levelname)s %(message)s'
flags = Args().flags
is_debug = '--debug' in flags or '-d' in flags
LOG_LEVEL = 'DEBUG' if is_debug else 'NORMAL'
coloredlogs.install(level=LOG_LEVEL, fmt=logFormat)

class PexelCrawler(MongoCrawler):
    short_name = 'PX'
    full_name = "Pexels.com"
    base_url = 'https://www.pexels.com/?format=html&page={}'
    domain = 'www.pexels.com'
    def __init__(self):
        MongoCrawler.__init__(self, short_name, full_name, self.base_url, self.domain)

    def get_image_page_links(self, page_soup):
        article_tags = page_soup.select('article.photos__photo')
        return [article.find('a') for article in article_tags]

    def get_image_source_url(self, image_page_soup):
        return image_page_soup.find('a', class_='js-download')['href']

    def get_image_thumbnail_url(self, image_page_soup):
        return image_page_soup.find('img', class_='photo__img')['src']

    def get_tags_container(self, image_page_soup):
        return image_page_soup.find('ul', class_='list-padding')

class PicjumboCrawler(MongoCrawler):
    short_name = 'PJ'
    full_name = "PicJumbo"
    base_url = 'https://picjumbo.com/page/{}/'
    domain = 'www.picjumbo.com'
    def __init__(self):
        MongoCrawler.__init__(self, self.short_name, self.full_name, self.base_url, self.domain, nested_scrape=False)

    def get_image_containers(self, image_page_soup):
        return image_page_soup.find_all('div', class_='item_wrap')

    def get_image_source_url(self, image_page_soup):
        return "http://"+image_page_soup.find('img', class_='image')['src'][2:].split("?", 1)[0]

    def get_image_thumbnail_url(self, image_page_soup):
        return "http://"+image_page_soup.find('img', class_='image')['src'][2:].split("?", 1)[0]+"?&h=500"

    def get_image_page_url(self, image_page_soup):
        return image_page_soup.find('a', class_='button')['href']

    def get_tags_container(self, image_page_soup):
        return image_page_soup.find('div', class_='browse_more')

pexelcrawler = PicjumboCrawler()
pexelcrawler.crawl()
