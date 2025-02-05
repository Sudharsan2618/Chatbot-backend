import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
from langchain import HuggingFaceHub
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

@app.route('/healthcheck', methods=['GET'])
def health():
    """use to check the health"""
    try:
        health = "Success"
        return jsonify({"status": f"{health}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/query', methods=['POST'])
def process_query():
    try:
        data = request.get_json()
        
        # Extract the query and file_key
        query = data.get('query', '')
        file_key = data.get('file_key', 'none')  # Default to 'none' if not provided
        
        if not query:
            return jsonify({
                'status': 'error',
                'message': 'Query is required'
            }), 400

        if file_key and file_key != 'none':
            # Handle file-based chat case
            result = generate_file_response(query, file_key)
        else:
            # Handle regular chat case
            result = generate_text(query)
        
        return jsonify({
            'status': 'success',
            'result': result
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def generate_file_response(query, file_key):
    
    try:
        # Process file from S3
        vectorstore = process_s3_file(file_key)

        retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})
        print("Retriever created successfully")

        model = HuggingFaceHub(repo_id="mistralai/Mistral-7B-Instruct-v0.3", model_kwargs={'temperature': 0.5, 'max_new_tokens': 500},
                               huggingfacehub_api_token=HF_TOKEN)
        print("Model initialized successfully")

        qa = RetrievalQA.from_chain_type(llm=model, retriever=retriever, chain_type="stuff")
        print("QA chain created successfully")
        
        # Generate the answer
        response = qa.invoke(query)

        result = response.get("result", "Could not generate a response").strip()

        if result:
            # Ensure only the helpful content is returned
            helpful_answer = result.split("Helpful Answer:")[-1].strip()
            print("Helpful Answer:", helpful_answer)
            return helpful_answer
    except Exception as e:
        import traceback
        print("Error details:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

def generate_text(query):
    print("running generate text")
    try:
        llm_model = HuggingFaceHub(
            repo_id="mistralai/Mistral-7B-Instruct-v0.3",
            huggingfacehub_api_token=HF_TOKEN,
            model_kwargs={
                "temperature": 0.5,
                "max_length": 500
            }
        )

        response = llm_model(query)

        # result = response.get("result", "Could not generate a response").strip()

        # if result:
        #     # Ensure only the helpful content is returned
        #     helpful_answer = result.split("Helpful Answer:")[-1].strip()
        #     print("Helpful Answer:", helpful_answer)
        print(response)
        return response
    except Exception as e:
        import traceback
        print("Error details:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv("PORT", 5000)))

