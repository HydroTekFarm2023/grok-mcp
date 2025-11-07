import os
from dotenv import load_dotenv

load_dotenv()

# AWS Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "plant-disease-results")

# xAI Configuration
XAI_API_KEY = os.getenv("XAI_API_KEY")
MODEL_ID = os.getenv("MODEL_NAME", "grok-2-vision-1212")