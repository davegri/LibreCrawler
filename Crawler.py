from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from requests.exceptions import HTTPError
import signal
import sys
import time
from PIL import Image, ImageOps
from clint.textui import colored
import logging
logger = logging.getLogger('LibreCrawler')


global interrupted
interrupted = False

def signal_handler(signal, frame):
    global interrupted
    interrupted = True

class Crawler():
    def __init__(self, base_url, domain, first_page_url=None, nested_scrape=True):
        """
        current_page is used to track what page the crawler is on

        db_record is an instance of the model class Crawler and represents the associated
        record in the table that keeps track of the crawler in the database

        base_url is the page that is used in order to scrape images from,
        must contain {} where the page number should be

        domain_name is the domain name of the website.
        used to transform relateive urls into absolute urls.

        first_page_base_url is an optional argument to specify a special url just for the first page
        """
        self.base_url = base_url
        self.domain = domain
        self.first_page_url = first_page_url

        self.images_added = 0
        self.images_failed = 0
        self.images_duplicate = 0

    def make_absolute_url(self, url,):
        """
        returns an absolute url for a given url using the domain_name property
        example: '/photo/bloom-flower-colorful-colourful-9459/' returns 'https://www.pexels.com/photo/bloom-flower-colorful-colourful-9459/'
        where the domain_name is 'www.pexels.com'
        """
        protocol = "https://"
        return urljoin(protocol + self.domain, url)

    def strip_protocol(self, url):
        url = url.replace('https://www.', '')
        url = url.replace('http://www.', '')
        return url

    def request_url(self, page_url, attempts=5, delay=3, stream=False):
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36',
        }
        for i in range(attempts):
            try:
                response = requests.get(page_url, headers=headers, stream=stream)
                response.raise_for_status()
            except HTTPError as e:
                print (RED.format("page responded with "+str(response.status_code)+". trying again"+str(page_url)))
                time.sleep(delay)
            else:
                return response
        else:
            # failed to get the page raise an exception
            response.raise_for_status()

    def get_page_soup(self, response):
        return BeautifulSoup(response.text)

    def get_image_page_urls(self, page_soup):
        """
        returns a list of urls for each image on the page
        """
        image_page_links = self.get_image_page_links(page_soup)
        if not image_page_links:
            return
        image_page_urls = [ make_absolute_url(link['href']) for link in image_page_links if link ]

        return image_page_urls


    def crawl(self, start_page=None, full_crawl=True):
        print("Started Crawler for {}".format(self.domain))
        signal.signal(signal.SIGINT, signal_handler)
        current_page =  start_page or 1
        visited_page_urls = []

        while True:
            self.terminate_if_interrupted()
            current_page_url = self.base_url.format(current_page)
            if current_page == 1 and self.first_page_url:
                current_page_url = self.first_page_url

            current_page_response = self.request_url(current_page_url)
            current_page_url = current_page_response.url
            current_page_soup = self.get_page_soup(current_page_response)
            if current_page_url in visited_page_urls:
                self.terminate("Trying to visit a page that has already been visited.")

            logger.info('crawling page #{}'.format(current_page))
            logger.debug('URL: {}'.format(current_page_url))
            image_containers = self.get_image_containers(current_page_soup)
            image_page_urls = self.get_image_page_urls(current_page_soup)
            if image_containers:
                logger.debug('crawling image containers')
                self.crawl_image_containers(image_containers, full_crawl)

            elif image_page_urls:
                logger.debug('crawling image page urls')
                self.crawl_image_page_urls(image_page_urls, full_crawl)

            else:
                self.terminate("Could not get image containers or page urls! (Probably ran out of pages)")

            visited_page_urls.append(current_page_url)
            current_page += 1


    def crawl_image_containers(self, image_containers, full_crawl=False):
        for n, container in enumerate(image_containers):
            self.terminate_if_interrupted()
            logger.info('crawling image {} of {}'.format(n+1, len(image_containers)))
            if self.image_exists(self.get_image_page_url(container)):
                logger.info("Image already exists in database, moving on")
                if not full_crawl:
                    self.terminate("Not a full crawl, terminating")
                continue
            self.scrape_image(container, self.get_image_page_url(container))

    def crawl_image_page_urls(self, image_page_urls, full_crawl=False):
        for n, image_page_url in enumerate(image_page_urls):
            self.terminate_if_interrupted()
            logger.info('crawling image at: {} (image {} of {})'.format(image_page_url, n+1, len(image_page_urls)))
            if self.image_exists(image_page_url):
                logger.info("Image already exists in database, moving on")
                if not full_crawl:
                    self.terminate("Not a full crawl, terminating")
                continue
            try:
                image_page_soup = self.get_page_soup(self.request_url(image_page_url))
            except HTTPError as e:
                logger.error("Failed to reach image page url at: {} , moving on".format(image_page_url))
                logger.debug(str(e))
                self.images_failed+=1
                continue
            self.scrape_image(image_page_soup, image_page_url)

    def terminate(self, message):
        logger.info(message)
        self.print_terminate_message()
        sys.exit()

    def terminate_if_interrupted(self):
        global interrupted
        if interrupted:
            self.terminate("interrupted")

    def print_terminate_message(self):
        logger.info("Crawling halted.")
        logger.info(colored.green("{} images added to database".format(self.images_added)))
        logger.info(colored.blue("{} images already existed from another website".format(self.images_failed)))
        logger.info(colored.yellow("{} images failed to add".format(self.images_failed)))

    def scrape_image(self, image_container_soup=None, image_page_url=None):
        logger.info('getting image source url')

        try:
            image_source_url = self.get_image_source_url(image_container_soup)
        except (AttributeError, TypeError) as e:
                logger.error("There was a problem getting the image source url for this image, moving on")
                logger.debug(str(e))
                self.images_failed+=1
                return

        # if no page url is supplied use source url as page url
        if image_page_url is None:
            logger.debug('no image_page_url supplied, using source url as page url')
            image_page_url = image_source_url

        logger.info('getting image thumbnail url')
        try:
            image_thumbnail_url = self.get_image_thumbnail_url(image_container_soup)
        except AttributeError as e:
                logger.error("There was a problem getting the thumbnail url for this image, moving on")
                logger.debug(str(e))
                self.images_failed+=1
                return

        logger.info('getting tags')
        try:
            tags = self.get_tags(image_container_soup)

        except AttributeError as e:
            logger.error("There was a problem getting the tags for this image, moving on")
            logger.debug(str(e))
            self.images_failed+=1
            return

        logger.info ('storing image in db')
        self.store_image(image_source_url, image_page_url, image_thumbnail_url, tags)

    def image_exists(self, image_page_url):
        raise NotImplementedError("method image_exists must be implemented")

    def get_image_page_links(self, page_soup):
        pass

    def get_image_containers(self, page_soup):
        raise NotImplementedError("method get_image_containers must be implemented")

    def get_image_page_url(self, page_soup):
        raise NotImplementedError("method get_image_page_url must be implemented ")

    def get_image_source_url(self, image_page_soup):
        raise NotImplementedError("method get_image_source_url must be implemented")

    def get_image_thumbnail_url(self, image_page_soup):
        raise NotImplementedError("method get_image_thumbnail_url must be implemented")

    def get_tags_container(self, image_page_soup):
        raise NotImplementedError("method get_tags_container must be implemented")

    def store_image(self, image_source_url, image_page_url, image_thumbnail_url, tags):
        raise NotImplementedError("method store_image must be implemented")

    def get_tags(self, image_page_soup):
        tags_container = self.get_tags_container(image_page_soup)
        tag_links = tags_container.find_all('a')
        tag_names = [tag_link.string.replace('#', '') for tag_link in tag_links if tag_link.string]
        return tag_names

    def create_thumbnail(self, url):
        logger.info('creating thumbnail from url: '+url)
        response = self.request_url(url, stream=True)
        size = 500, 500
        img = Image.open(response.raw)
        thumb = ImageOps.fit(img, size, Image.ANTIALIAS)
        return thumb
