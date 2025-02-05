import boto3
from langchain_community.document_loaders import WebBaseLoader
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEndpoint
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv
import fitz
import os

# Load environment variables for AWS
load_dotenv()
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION')
BUCKET_NAME = os.getenv('BUCKET_NAME')
HF_TOKEN = os.getenv('HF_TOKEN')

# Print the HF_TOKEN to verify it's loaded correctly
print(f"HF_TOKEN: {HF_TOKEN}")

# Initialize S3 client (Make sure to set AWS credentials in your environment variables or AWS config file)
s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

BUCKET_NAME = "companian"


def extract_text_from_pdf(file_path):
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text("text")  # Ensures plain text extraction
    return text


def process_s3_file(file_key):
    # Check if file_key is None
    if not file_key:
        raise ValueError("File key is None. Ensure the key is correctly passed to the function.")

    print("download starting")
    # Download file from S3
    s3.download_file(BUCKET_NAME, file_key, file_key)
    print("download Finished")
    

    # Extract and clean up text from the PDF
    text = extract_text_from_pdf(file_key)
    # Remove any extraneous whitespace or non-printable characters
    content = text.strip()
    
    # Wrap content in Document objects
    documents = [Document(page_content=content)]
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=50)
    chunks = text_splitter.split_documents(documents)

    # Initialize embeddings
    embeddings = HuggingFaceInferenceAPIEmbeddings(api_key=HF_TOKEN, model_name="pinecone/bert-retriever-squad2")
    vectorstore = Chroma.from_documents(chunks, embeddings)

    print("File downloaded and embedded successfully!")
    return vectorstore
