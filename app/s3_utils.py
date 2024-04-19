import uuid
import boto3
import os
import mimetypes

s3_client = boto3.client(
    's3'
)
s3_bucket_name = 'comfyspace'
aws_region = os.environ.get('AWS_DEFAULT_REGION', '')

def upload_file_to_s3(image_location):
    file_extension = os.path.splitext(image_location)[1]
    with open(image_location, "rb") as input_file:
        output = input_file.read()
    
    file_name = str(uuid.uuid4())[:21]

    s3_key = f"outputs/{file_name}{file_extension}"
    
    mime_type = guess_mime_type(image_location)
    print(f"📄 Uploading type {mime_type} to S3 {s3_key}")
    # Upload to S3
    s3_client.put_object(Bucket=s3_bucket_name, Key=s3_key, Body=output, ContentType=mime_type)
    print(f"✅ Uploaded {image_location} to S3 {s3_key}")
    return f'https://{s3_bucket_name}.s3.{aws_region}.amazonaws.com/{s3_key}'

def guess_mime_type(file_name):
    mime_type, _ = mimetypes.guess_type(file_name)
    return mime_type or 'application/octet-stream'