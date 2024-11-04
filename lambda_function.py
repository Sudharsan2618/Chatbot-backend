import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
from langchain_community.llms import HuggingFaceHub
from langchain_huggingface import HuggingFaceEndpoint
from langchain.chains import RetrievalQA
from s3_processing import process_s3_file
from pydantic import BaseModel
import json

# Load environment variables for AWS
load_dotenv()

# Initialize Flask app and CORS
app = Flask(__name__)
CORS(app)


AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION')
BUCKET_NAME = os.getenv('BUCKET_NAME')
HF_TOKEN = os.getenv('HF_TOKEN')

# Initialize S3 client with environment variables
s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def lambda_handler(event, context):
    """Main Lambda handler to route requests based on path."""
    try:
        route = event['path']
        
        if route == '/upload' and event['httpMethod'] == 'POST':
            return upload_file(event)
        elif route == '/query' and event['httpMethod'] == 'POST':
            return process_query(event)
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Route not found'})
            }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def upload_file(event):
    """Handle file upload to S3."""
    try:
        file_content = event['body']
        file_key = event['headers'].get('file-name')
        
        if not file_key:
            raise ValueError("File key is required in the header 'file-name'")

        # Upload file to S3
        s3.put_object(Bucket=BUCKET_NAME, Key=file_key, Body=file_content)
        return {
            'statusCode': 200,
            'body': json.dumps({"file_key": file_key})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({"error": str(e)})
        }

def process_query(event):
    """Process a query based on content in an S3 file."""
    try:
        data = json.loads(event['body'])
        file_key = data.get('file_key')
        question = data.get('question')

        # Process file from S3 and initialize vectorstore
        vectorstore = process_s3_file(file_key)
        retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})

        # Initialize model for RetrievalQA
        model = HuggingFaceEndpoint(repo_id="mistralai/Mistral-7B-Instruct-v0.2", 
                                    temperature=0.2, max_new_tokens=512)
        
        qa = RetrievalQA.from_chain_type(llm=model, retriever=retriever, chain_type="stuff")

        # Generate answer
        response = qa.invoke(question)
        result = response.get("result", "Could not generate a response")
        
        return {
            'statusCode': 200,
            'body': json.dumps({"result": result})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({"error": str(e)})
        }
