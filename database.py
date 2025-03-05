import pymongo
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId
from typing import List, Optional

app = FastAPI()

client = pymongo.MongoClient("localhost", 27017)
db = client["news_database"]

articles_collection = db["articles"]

class Article(BaseModel):
    title: str
    content: str
    source: str
    published_date: Optional[str] = datetime.utcnow().strftime("%Y-%m-%d")
    url: Optional[str] = None
    tags: List[str] = []
    
@app.post("/articles/")
def add_article(article: Article):
    article_data = article.model_dump()
    result = articles_collection.insert_one(article_data)
    
    return {"message": "Article added", "id": str(result.inserted_id)}


@app.get("/articles/")
def get_articles(source: Optional[str] = None, tag: Optional[str] = None):
    """
    Gets all articles with optional filters by source and tags
    
    params:
        source: news source (e.g., NYT, BBC)
        tag: category (e.g., AI, politics)
    """
    query = {}
    if source:
        query["source"] = source
        
    if tag:
        query["tags"] = tag
        
    articles = []
    for article in articles_collection.find(query):
        article["_id"] = str(article["_id"])
        articles.append(article)
    return articles

@app.get("/articles/{article_id}")
def get_article(article_id: str):
    """
    Gets an individual article based on given ID
    
    param:
        article_id: unique ID associated with article in the database
    """
    article = articles_collection.find_one({"_id": ObjectId(article_id)})
    if article:
        article["_id"] = str(article["_id"])
        return article
    
    raise HTTPException(status_code=404, detail="Article not found")


@app.get("/articles/search/")
def search_articles(q: str = Query(..., description="Search query")):
    """
    Searches for specified text across articles
    
    param:
        q: specific text to search for
        
    returns:
        - articles if any matches found
        - error message otherwise 
    """
    results = articles_collection.find({"$text": {"$search": q}})
    articles = [{"_id": str(article["_id"]), **article} for article in results]
    return articles if articles else {"message": "No matching articles found"}
    



