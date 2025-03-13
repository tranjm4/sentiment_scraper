from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import time
from datetime import datetime

import threading

import requests

import pymongo
from pprint import pprint

class BBCWebCrawler:
    def __init__(self, max_depth=5):
        self.max_depth = max_depth
        self.visited_links = set()
        self.base_url = "https://www.bbc.com"
        self.start_urls = self._get_start_urls()
        
        self.start_article_urls = []
        
        self.article_urls = []
        
        self._get_start_articles()
        
    def _get_start_urls(self):
        """
        Using base_url, gets all start_urls
        Semantically, they are each section from the navbar
        
        returns:
            urls: URL of each news category obtained from the home page
        """
        response = requests.get(self.base_url)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            div = soup.find("nav", attrs={"data-testid": "level1-navigation-container"})
            a = div.find_all("a")
            hrefs = [x['href'] for x in a[1:-3] if x.get_text() != 'Sport'] # remove Home, Audio, Video, Live
            urls = [self.base_url + href for href in hrefs]
            
            return urls
        else:
            print(f"Error fetching website HTML at {self.base_url}: {response}")
        
        
    def _get_start_articles(self):
        """
        Using start_urls, collect all articles from them
        
        Populates start_article_urls with found URLs
        """
        for url in self.start_urls:
            response = requests.get(url)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                divs = soup.find_all("div", attrs={"data-indexcard": "true"})
                for div in divs:
                    try:
                        href = div.find("a")["href"]
                        if self._filter_href(href) == False:
                            continue
                        link = href if href.startswith("http") else self.base_url + href
                        self.start_article_urls.append(link)
                        self.visited_links.add(link)
                    except:
                        continue
            else:
                print(f"Error retrieving HTML content from {url}\nError response: {response}")
            
    def crawl(self):
        """
        Performs a BFS starting from the given article_urls
        """
        url_queue = []
        for url in self.start_article_urls:
            url_queue.append(url)
        depth = 0
        while len(url_queue) > 0 and depth < self.max_depth:
            # traverse single layer of URLs
            threads = []
            layer_size = len(url_queue)
            print(f"{'-'*50}\nLayer Size: {layer_size}\n{'-'*50}")
            for i in range(layer_size):
                print(f"Crawling article {i+1}...")
                url = url_queue.pop(0)
                print(url)
                # thread = threading.Thread(
                #     target=self.crawl_article,
                #     args=(url, depth)
                # )
                
                # threads.append(thread)
                # thread.start()
                self.crawl_article(url, depth)
                
                print("Done")
                print()
                time.sleep(0.5)
            
            # for thread in threads:
            #     thread.join()
            layer_size = len(url_queue)
            depth += 1
            print(f"\n{'*'*50}\nIncreasing depth to {depth}\n{'*'*50}\n")
            
    def crawl_article(self, url, current_depth):
        """
        Crawls article, scraping information
        Collects:
            - title
            - author
            - date
            - content
            - tag(s)
        
        Note: this function is run by multiple threads, so caution
        using shared resources (e.g., article_urls, accessing database)
        is highly advised
        """
        if current_depth > self.max_depth:
            return
        response = requests.get(url)
        
        if response.status_code == 200:
            # collect data
            soup = BeautifulSoup(response.text, "html.parser")
            title, author, date, content, tags = self.parse_soup(soup)
            
            print(any([x == None for x in [title, author, date, content, tags]]))
            
            # add data to database
            add_to_db(title, author, date, content, tags, url, "BBC")
            
            # get articles to add to queue
            self.get_neighbor_articles(soup)
            
            return
            
        else:
            print(f"Error fetching article at {url}\nError response: {response}")
        
        # might not need driver because traversing by article
        # driver = setup_selenium_webdriver()
        # driver.get(url)
        
    def parse_soup(self, soup):
        """
        Helper function that scrapes all necessary information 
        from a BBC article
        """
        title = self.get_title(soup)
        author = self.get_author(soup)
        date = self.get_date(soup)
        content = self.get_content(soup)
        tags = self.get_tags(soup)
        
        return title, author, date, content, tags
    
    def get_title(self, soup):
        """
        Retrives title from article soup
        """
        try:
            title = soup.find("h1").get_text()
            return title
        except:
            return None
    
    def get_author(self, soup):
        """
        Retrieves author from article soup
        """
        try:
            div = soup.find("div", attrs={"data-testid":"byline-new-contributors"})
            author = div.find("span").get_text()
            return author
        except:
            return None
        
    def get_date(self, soup):
        """
        Retrieves the publish date from article soup
        """
        try:
            date = soup.find("meta", attrs={"name":"article:modified_time"})['content']
            # parse date
            parsed_date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")
            return parsed_date.isoformat()
        except:
            return None
        
    def get_content(self, soup):
        """
        Retrieves the textual content from the article given the article soup
        """
        try:
            divs = soup.find_all("div", attrs={"data-component":"text-block"})
            text = ' '.join([div.get_text() for div in divs])
            return text
        except:
            return None
        
    def get_tags(self, soup):
        """
        Retrieves content category tags from the article soup
        """
        try:
            div = soup.find("div", attrs={"data-component":"tags"})
            tags = [a.get_text() for a in div.find_all("a")]
            return tags
        except:
            return None
        
    def get_neighbor_articles(self, soup):
        """
        Given soup, finds other related articles via hrefs
        
        Appends found URLs to article_urls
        Returns None
        """
        try:
            div = soup.find("div", attrs={"data-analytics_group_name":"More"})
            hrefs = [a['href'] for a in div.find("a")]
            for href in hrefs:
                if self._filter_href(href) == False:
                    continue
                link = href if href.startswith("http") else self.base_url + href
                if link in self.visited_links:
                    continue
                self.article_urls.append(link)
                self.visited_links.add(link)
        except:
            return
        
    def _filter_href(self, href):
        """
        Filters the href. 
        Returns False if it contains certain paths (i.e., "audio", "videos", "live"),
        Returns True otherwise
        """
        ignore_paths = ["audio", "videos", "video", "reel", "live"]
        href_paths = href.split("/")
        return not any([ignore_path in href_paths for ignore_path in ignore_paths])

def setup_selenium_webdriver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), 
        options=options
    )
    
    return driver

def add_to_db(title, author, date, content, tags, url, source="BBC"):
    article = {
        "title": title,
        "author": author,
        "published_date": date,
        "source": source,
        "content": content,
        "tags": tags,
        "url": url
    }
    print(f"Posting to DB...", end="")
    response = requests.post("http://localhost:8000/articles/", json=article, timeout=100)
    print(f" response: {response}")

def main():
    # driver = setup_selenium_webdriver()
    # start_urls = ["https://www.bbc.com/news", "https://www.bb.com/innovation"]
    # start_url = "https://www.bbc.com"
    # base_url = "https://www.bbc.com"
    # urls = crawl_site(start_url, base_url)
    # print(urls)
    
    crawler = BBCWebCrawler(max_depth=3)
    crawler.crawl()
    
    # threads = []
    # for url in urls:
    #     thread = threading.Thread(target=parse_links,
    #                               args=(url, base_url))
    #     threads.append(thread)
    #     thread.start()
    
    # # wait for threads to finish
    # for thread in threads:
    #     thread.join()
    
    

# driver = webdriver.Chrome()
# driver.get("https://www.bbc.com/innovation")

# buttons = driver.find_elements(By.CLASS_NAME, "sc-944f9211-2")[1:-2]
# for i in range(5):
#     button = driver.find_elements(By.CLASS_NAME, "sc-944f9211-2")[i+1]
#     button.click()  # Simulate clicking the button

#     new_url = driver.current_url  # Capture the redirected URL
#     print("Redirected to:", new_url)
    
#     time.sleep(10)

# driver.quit()

if __name__ == '__main__':
    main()