import faiss
import numpy as np


import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
import llm.rag.embedding as embedding
import database


def construct_vector_db(client):
    articles = client["database"]["articles"]
    
    model = embedding.initialize_transformer()
    article_embeddings = embedding.embed_articles(articles, model)
    
    return article_embeddings
    
def construct_faiss_index(embeddings):
    embedding_array = np.array(embeddings).astype("float32")
    index = faiss.IndexFlatL2(embedding_array.shape[1])
    
    return index

def store_vector_db(index):
    faiss.write_index(index, "faiss_index.index")

def main():
    client = database.connect_to_db()
    
    embeddings = construct_vector_db(client)
    
    index = construct_faiss_index(embeddings)
    store_vector_db(index)
    

if __name__ == "__main__":
    main()
