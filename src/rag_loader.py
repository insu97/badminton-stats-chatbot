import os
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()

REVIEWS_DIR = "data/reviews"
FAISS_DIR = "db/faiss"

def load_reviews():
    """txt 파일 로드 - 파일명에서 날짜 추출해서 메타데이터에 추가"""
    loader = DirectoryLoader(
        REVIEWS_DIR,
        glob="*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )
    documents = loader.load()

    # 파일명에서 날짜 추출해서 메타데이터에 추가
    for doc in documents:
        filename = os.path.basename(doc.metadata.get("source", ""))
        date_match = re.search(r'(\d{8})', filename)
        if date_match:
            date_str = date_match.group(1)
            formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
            doc.metadata["date"] = formatted_date
            # 날짜를 문서 내용 앞에 추가해서 검색 정확도 향상
            doc.page_content = f"[날짜: {formatted_date}]\n{doc.page_content}"

    print(f"✅ {len(documents)}개 파일 로드 완료")
    return documents

def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(documents)
    print(f"✅ {len(chunks)}개 청크 분할 완료")
    return chunks

def create_vector_store(chunks):
    embeddings = OpenAIEmbeddings(
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    os.makedirs(FAISS_DIR, exist_ok=True)
    vector_store = FAISS.from_documents(chunks, embeddings)
    vector_store.save_local(FAISS_DIR)
    print("✅ Vector DB 저장 완료!")
    return vector_store

def get_retriever():
    embeddings = OpenAIEmbeddings(
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    vector_store = FAISS.load_local(
        FAISS_DIR,
        embeddings,
        allow_dangerous_deserialization=True
    )
    return vector_store.as_retriever(search_kwargs={"k": 3})

if __name__ == "__main__":
    documents = load_reviews()
    chunks = split_documents(documents)
    create_vector_store(chunks)