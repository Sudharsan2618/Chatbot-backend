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

@app.route('/cvSuggesion', methods=['POST'])
def sv_suggession():
    """Endpoint to process a query based on content in an S3 file."""
    data = request.get_json()
    file_key = data.get('file_key')
    job_description = data.get('job_description')
    print('file_key:', file_key)
    print('job_description:', job_description)

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
        response = qa.invoke("""
            I want you to act as my resumer reviewer. here i am sending the jon discription that i am going to apply 
            and also i am giving my resume to you. i want you to make a clear cut view on what are the 
            things, keywors, skills that i want to change in resume to ace this job interview. So use my embadded resume and i want you to give suggession according to that resume
            . make your suggession less than 600 words. This is the job discription : {job_description}""")

        result = response.get("result", "Could not generate a response")
        print("response",result)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def generate_email_variants(first_name, last_name, domain):
    # Generate common email patterns
    email_patterns = [
        f"{first_name}{last_name[0]}@{domain}",
        f"{first_name}@{domain}",
        f"{first_name}{last_name}@{domain}",
        f"{first_name}.{last_name}@{domain}",
        f"{first_name}_{last_name}@{domain}",
        f"{first_name[0]}.{last_name}@{domain}",
        f"{first_name}.{last_name[0]}@{domain}",
        f"{last_name}{first_name}@{domain}",
    ]
    return email_patterns

def validate_email(email):
    try:
        domain = email.split('@')[1]
        records = dns.resolver.resolve(domain, 'MX')
        mx_record = str(records[0].exchange)

        # Establish SMTP connection
        server = smtplib.SMTP(mx_record)
        server.helo()
        server.mail('madsan123456@gmail.com')
        code, message = server.rcpt(email)
        server.quit()

        return code == 250
    except Exception as e:
        print(f"Error validating email {email}: {e}")
        return False

@app.route('/find-email', methods=['POST'])
def find_email():
    data = request.json

    # Extract input fields
    first_name = data.get('first_name', '').strip().lower()
    last_name = data.get('last_name', '').strip().lower()
    domain = data.get('domain', '').strip().lower()

    if not first_name or not last_name or not domain:
        return jsonify({"error": "Please provide first_name, last_name, and domain"}), 400

    # Generate email variants
    email_variants = generate_email_variants(first_name, last_name, domain)

    # Validate emails
    for email in email_variants:
        if validate_email(email):
            return jsonify({"valid_email": email}), 200

    # If no valid email is found
    return jsonify({"message": "Sorry, not able to find a valid email ID."}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv("PORT", 5000)))

