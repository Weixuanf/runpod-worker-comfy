from nanoid import generate
import boto3
import os
import mimetypes
from app.common import COMFYUI_LOG_PATH

s3_client = boto3.client(
    's3'
)
s3_bucket_name = 'comfyspace'
aws_region = os.environ.get('AWS_DEFAULT_REGION', '')

last_log_time = 0
def upload_log_to_s3(file_key):
    if not os.path.exists(COMFYUI_LOG_PATH):
        raise Exception(f"Log file {COMFYUI_LOG_PATH} not found")
    if not file_key or file_key == "":
        raise Exception("File key is required to upload log")
    print(f"📄 Uploading log to S3 {file_key}")
    with open(COMFYUI_LOG_PATH, "r") as f:
        log_data = f.read()
    s3_client.put_object(Bucket=s3_bucket_name, Key=file_key, Body=log_data)
    last_log_time = last_log_time + 1
    if last_log_time % 5 == 0:
        print(f"✅ Uploaded log to S3 {file_key}")

def upload_file_to_s3(image_location):
    file_extension = os.path.splitext(image_location)[1]
    with open(image_location, "rb") as input_file:
        output = input_file.read()
    
    file_name = str(generate(size=18))

    s3_key = f"output/{file_name}{file_extension}"
    
    mime_type = guess_mime_type(image_location)
    print(f"📄 Uploading type {mime_type} to S3 {s3_key}")
    # Upload to S3
    s3_client.put_object(Bucket=s3_bucket_name, Key=s3_key, Body=output, ContentType=mime_type)
    print(f"✅ Uploaded {image_location} to S3 {s3_key}")
    # return f'https://{s3_bucket_name}.s3.{aws_region}.amazonaws.com/{s3_key}'
    # return f"{file_name}{file_extension}"
    return f"{s3_key}"

def guess_mime_type(file_name):
    mime_type, _ = mimetypes.guess_type(file_name)
    return mime_type or 'application/octet-stream'