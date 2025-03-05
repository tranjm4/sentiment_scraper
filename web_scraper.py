from bs4 import BeautifulSoup
import scrapy


class ArticleSpider(scrapy.Spider):
    name = 'articlespider'
    start_urls = ['https://www.bbc.com/news']
    base_url = 'https://www.bbc.com'
    
    def parse(self, response):
        """
        Extracts article URLs from the home page
        """
        soup = BeautifulSoup(response.text, "html.parser")
        divs = soup.find_all("div", attrs={"data-testid": "dundee-card"})
        links = [div.find("a")['href'] for div in divs]
        
        for link in links:
            url = link if link.startswith("http") else ArticleSpider.base_url + link
            yield response.follow(link, self.parse_article)
    
    def parse_article(self, response):
        """
        Parses individual article
        
        Returns:
            - title
            - text
            - author
            - tag(s)
        """
        soup = BeautifulSoup(response.text, "html.parser")
        
        # attempt to get title
        try:
            title = soup.find("h1").text
        except AttributeError:
            title = None
        
        # attempt to get text
        try:
            text_divs = soup.find_all("div", attrs={"data-component": "text-block"})
            text = " ".join(div.get_text() for div in text_divs)
        except:
            text = None
            
        # attempt to get author
        try:
            author_div = soup.find("div", attrs={"data-testid": "byline-new-contributors"})
            author = author_div.find("span").text
        except:
            author = None
            
        # attempt to get tags
        try:
            tag_div = soup.find("div", attrs={"data-component": "tags"})
            tags = [a.text for a in tag_div.find_all("a")]
        except:
            tags = None
        
        yield {
            "url": response.url,
            "title": title,
            "author": author,
            "content": text,
            "tags": tags,
            "status_code": response.status,
            "headers": dict(response.headers)
        }
        
        
            