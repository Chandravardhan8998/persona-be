from typing import Iterable

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai.types import ResponseFormatJSONSchema
from openai.types.chat import ChatCompletionFunctionMessageParam, ChatCompletionToolMessageParam, \
    ChatCompletionAssistantMessageParam, ChatCompletionUserMessageParam, ChatCompletionSystemMessageParam, \
    ChatCompletionDeveloperMessageParam
from qdrant_client import QdrantClient, models
from openai import OpenAI
import os
from pathlib import Path

from qdrant_client.http.models import Document

load_dotenv()
qdb_api = os.getenv("QDRANT_DB_API")
qdb_url = os.getenv("QDRANT_DB_URL")
collection="learning_vectors"
document="learning_vectors_doc"
async def manage_collection_building():
    q_client = QdrantClient(url=qdb_url, api_key=qdb_api)
    is_exist = q_client.collection_exists(collection)
    if not is_exist:
        try:
            q_client.create_collection(collection_name=collection, vectors_config=models.VectorParams(size=100, distance=models.Distance.COSINE), )
            return True
        except:
            print("failed to create database")
            return False
    return True

def use_splitter(file:Path):
    # Loading
    loader = PyPDFLoader(file_path=file)
    docs = loader.load()  # Read PDF File

    # Chunking
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=400
    )
    split_docs = text_splitter.split_documents(documents=docs)
    return split_docs


def embedd_vector_db(split_text: list[Document]) -> bool | QdrantVectorStore:
    try:
        embedding_model = OpenAIEmbeddings(
            model="text-embedding-3-large"
        )
        vector_db = QdrantVectorStore.from_documents(
            documents=split_text,
            url=qdb_url,
            collection_name=collection,
            embedding=embedding_model,
            force_recreate=True,
            api_key=qdb_api
        )
        return vector_db
    except Exception as e:
        print(e)
        return False

async def get_embedd_doc(file:Path):
    # Vector Embeddings
    print("start")
    collection_exist= await manage_collection_building()
    print("collection_exist ",collection_exist)
    if not collection_exist:
        return {"isSuccess":False,"message":"Something wrong with collection."}

    split_text=use_splitter(file)
    print(split_text)
    if len(split_text)==0:
        return {"isSuccess":False,"message":"Something wrong with documents."}

    vector_db = embedd_vector_db(split_text)
    print(vector_db)
    if not vector_db:
        return {"isSuccess":False,"message":"Embedding failed."}
    print("vector_db ",vector_db)
    return {"isSuccess":True,"message":"Embedded successfully."}


async def get_rag_response(query:str):
    client = OpenAI()

    # Vector Embeddings
    embedding_model = OpenAIEmbeddings(
        model="text-embedding-3-large"
    )
    vector_db = QdrantVectorStore.from_existing_collection(
        url=qdb_url,
        api_key=qdb_api,
        collection_name=collection,
    embedding=embedding_model
    )
        # embedding=embedding_model,
        # documents=split_text,split_text
    search_results = vector_db.similarity_search(
        query=query
    )
    print("search_results ",search_results)

    context = "\n\n\n".join([ f"Page Content: {result.page_content}\nPage Number: {result.metadata['page_label']}\nFile Location: {result.metadata['source']}"
                                for result in search_results])

    SYSTEM_PROMPT = f"""
        You are a helpful AI Assistant who answers user query based on the available context
        retrieved from a PDF file along with page_contents and page number.

        You should only ans the user based on the following context and navigate the user
        to open the right page number to know more.
        Context:
        {context}
    """
    system_message=ChatCompletionSystemMessageParam(role="system",content=SYSTEM_PROMPT)
    user_message=ChatCompletionUserMessageParam(role="user",content=query)
    messages=[
            system_message,
            user_message,
        ]
    chat_completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )
    print(f"🤖: {chat_completion.choices[0].message.content}")
    return f"🤖: {chat_completion.choices[0].message.content}"

