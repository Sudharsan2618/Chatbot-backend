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

@app.route('/upload', methods=['POST'])
def upload_file():
    """Endpoint to upload a file to the specified S3 bucket."""
    try:
        file = request.files['file']
        file_key = file.filename
        s3.upload_fileobj(file, BUCKET_NAME, file_key)
        return jsonify({"file_key": f"{file_key}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/query', methods=['POST'])
def process_query():
    """Endpoint to process a query based on content in an S3 file."""
    data = request.get_json()
    file_key = data.get('file_key')
    question = data.get('question')
    print('file_key:', file_key)
    print('question:', question)

    try:
        # Process file from S3
        vectorstore = process_s3_file(file_key)

        retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})
        print("Retriever created successfully")

        model = HuggingFaceEndpoint(repo_id="mistralai/Mistral-7B-Instruct-v0.2", 
                                    temperature=0.2, max_new_tokens=512)
        print("Model initialized successfully")

        qa = RetrievalQA.from_chain_type(llm=model, retriever=retriever, chain_type="stuff")
        print("QA chain created successfully")
        
        # Generate the answer
        response = qa.invoke(question)

        result = response.get("result", "Could not generate a response")
        print("response",result)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=5001)
