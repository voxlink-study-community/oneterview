import os
import pandas as pd
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
import tiktoken  # OpenAI의 토큰 계산 라이브러리
# from dotenv import load_dotenv
# import os
# load_dotenv()
# OPENAI_API_KEY = os.environ["OPENAI_API_KEY"] 
# ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"] 
# GEMINI_API_KEY = os.environ["GEMINI_API_KEY"] 
# OpenAI API 설정
embedding_model = "text-embedding-3-small"  # 선택한 모델
model_price_per_1k_tokens = 0.0004  # text-embedding-3-small의 1k 토큰당 비용 (달러)

# 1. CSV 데이터 로드
csv_file = "/home/youngoh/phase3/oneterview/cv_csv/CV_test100.csv"  # CSV 파일 경로
df = pd.read_csv(csv_file)

# 2. 텍스트 결합 (Q1 ~ Q8 컬럼)
text_columns = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"]
df["combined_text"] = df[text_columns].fillna("").apply(
    lambda row: " ".join(row), axis=1
)

# 3. 토큰 계산 함수 정의
tokenizer = tiktoken.get_encoding("cl100k_base")  # OpenAI 기본 토크나이저 사용
def count_tokens(text):
    return len(tokenizer.encode(text))

# 텍스트 데이터의 토큰 수 계산
df["token_count"] = df["combined_text"].apply(count_tokens)

# 총 토큰 수 계산
total_tokens = df["token_count"].sum()
total_cost = (total_tokens / 1000) * model_price_per_1k_tokens

print(f"총 토큰 수: {total_tokens}")
print(f"API 비용 (달러): ${total_cost:.6f}")

# 4. 텍스트 데이터를 Document 형식으로 변환
documents = [
    Document(
        page_content=row["combined_text"],
        metadata={
            "Company Name": row["Company Name"],
            "Position/Task": row["Position/Task"],
            "Apply Period": row["Apply Period"],
            "School Name": row["School Name"],
            "Department": row["Department"],
            "GPA (Obtained)": row["GPA (Obtained)"],
            "GPA (Base)": row["GPA (Base)"],
            "Specification": row["Specification"],
        },
    )
    for _, row in df.iterrows()
]

# 5. 텍스트 분할 및 임베딩 생성
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
split_docs = text_splitter.split_documents(documents)

embeddings = OpenAIEmbeddings(model=embedding_model)
vector_store = FAISS.from_documents(split_docs, embeddings)

# 6. 검색 함수 정의
def search_company_and_position(company_name, position_task, top_k=3):
    # 검색 쿼리 생성
    query_text = f"{company_name} {position_task}"
    query_embedding = embeddings.embed_query(query_text)

    # 벡터 스토어에서 유사한 문서 검색
    results = vector_store.similarity_search_by_vector(query_embedding, k=top_k)
    
    # 결과 반환
    for result in results:
        print("----- 검색 결과 -----")
        print("Company Name:", result.metadata["Company Name"])
        print("Position/Task:", result.metadata["Position/Task"])
        print("Apply Period:", result.metadata["Apply Period"])
        print("School Name:", result.metadata["School Name"])
        print("Department:", result.metadata["Department"])
        print("GPA (Obtained):", result.metadata["GPA (Obtained)"])
        print("GPA (Base):", result.metadata["GPA (Base)"])
        print("Specification:", result.metadata["Specification"])
        print("Text Content:", result.page_content[:500])  # 일부 내용만 출력
        print("---------------------")

# 7. 벡터 스토어 저장
vector_store.save_local("faiss_vectorstore")

print("벡터 스토어에 데이터 저장 완료!")

# 8. 테스트: 검색 실행
search_company_and_position("포스코퓨처엠", "생산기술", top_k=1)
