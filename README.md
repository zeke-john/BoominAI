# BoominAI

Finetuning Music-gen for specififcaly hiphop, rap, and trap beats

# Activate env:

pyenv activate BeatzAI

# for brew installs:

arch -x86_64 brew ...

# to get beats from yt:

CREATE A FOLDER WITH THE ARTIST'S NAME

yt-dlp --extract-audio --audio-format mp3 -o '/Users/zeke/Documents/Github/AI-Beatz/{NAME OF ARTIST AKA FOLDER NAME}/%(title)s.%(ext)s' "https://www.youtube.com/@THEIR_YOUTUBE_HANDLE/videos"
data/training_data

# check number of files and size of s3 bucket

aws s3 ls "s3://westai/output/" --summarize

# upload to s3 bucket

import boto3
import os

ACCESS_ID = ''
ACCESS_KEY = ''

def upload_files(path, bucket_name, s3_folder):
session = boto3.Session(
aws_access_key_id=ACCESS_ID,
aws_secret_access_key=ACCESS_KEY,
)

    s3 = session.resource('s3')
    bucket = s3.Bucket(bucket_name)

    for root, dirs, files in os.walk(path):
        for file in files:
            full_path = os.path.join(root, file)
            with open(full_path, 'rb') as data:
                s3_path = os.path.join(s3_folder, os.path.relpath(full_path, path))
                print(s3_path)
                bucket.put_object(Key=s3_path, Body=data)

if **name** == "**main**":
upload_files('/Users/zeke/Documents/Github/BoominAI/output', 'westai', 'output')

# get test drake model from gdown

!pip install --upgrade --no-cache-dir gdown

!gdown 1apJUdQql8HC2xO6FWCoAJe0Uf0nlnUi7

# get beats from only X artists

import os
import shutil

source_directory = '/Users/zeke/Documents/Github/BoominAI/data/training_data'
destination_directory = '/Users/zeke/Documents/Github/BoominAI/smaller'

if not os.path.exists(destination_directory):
os.makedirs(destination_directory)

files = os.listdir(source_directory)

keywords = ['kanye', 'drake', '21 savage']

# Loop through files and copy those containing the keywords to the destination

for file_name in files:
for keyword in keywords:
if keyword.lower() in file_name.lower():
source_path = os.path.join(source_directory, file_name)
destination_path = os.path.join(destination_directory, file_name)
shutil.copy2(source_path, destination_path)
print(f"Copied {file_name} to {destination_directory}")

print("Copy process complete.")
