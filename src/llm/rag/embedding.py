from sentence_transformers import SentenceTransformer
import nltk

# nltk.download('punkt')
# nltk.download('punkt_tab')

import database

from argparse import ArgumentParser
from tqdm import tqdm

# model = SentenceTransformer("all-MiniLM-L6-v2")

def __get_cl_args():
    """
    Gets optional command line arguments (verbose and clear)
        - verbose: prints progress of embedding
        - clear: resets any existing embedding before performing the embedding
        
    Returns both values 
    """
    parser = ArgumentParser(prog="DocumentEmbedding",
                            description="Retrieves the documents in the database and creates embeddings")
    # verbose argument
    parser.add_argument("-v", "--verbose", action="store_true", default=True)
    # clear argument: clears embedding before performing embedding
    parser.add_argument("-c", "--clear", action="store_true", default=False)
    
    args = parser.parse_args()
    
    return args.verbose, args.clear

def initialize_transformer():
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    return model

def articles_to_list(articles):
    documents = [x["content"] for x in list(articles.find())]
    return documents

def chunk_text(text, max_length=512, overlap=128):
    sentences = nltk.sent_tokenize(text)
    chunks = []
    chunk = []
    length = 0
    
    for sentence in sentences:
        sentence_length = len(sentence.split())
        if length + sentence_length > max_length:
            chunks.append(" ".join(chunk))
            chunk = chunk[-(overlap//2):]
            length = sum(len(s.split()) for s in chunk)
            
        chunk.append(sentence)
        length += sentence_length
    
    if chunk:
        chunks.append(" ".join(chunk))
        
    return chunks

def chunk_articles(articles_list):
    article_chunks = []
    for article in tqdm(articles_list, desc="Chunking articles...", leave=True):
        chunks = chunk_text(article, max_length=512, overlap=128)
        for chunk in chunks:
            article_chunks.append(chunk)
            
    return article_chunks

def embed_articles(articles, model=None):
    articles_list = articles_to_list(articles)
    
    if model == None:
        model = initialize_transformer()
    
    article_chunks = chunk_articles(articles_list)
    # print(len(article_chunks))
    embeddings = model.encode(article_chunks, show_progress_bar=True)
    
    return embeddings

def main():
    verbose, clear = __get_cl_args()
    
    client = database.connect_to_db()
    articles = client["database"]["articles"]   # get articles collection from mongodb database

    article_embeddings = embed_articles(articles)

if __name__ == "__main__":
    main()