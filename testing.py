# # from audiocraft.models import musicgen
# # from audiocraft.utils.notebook import display_audio
# # import torch

# # model = musicgen.MusicGen.get_pretrained('medium', device='cuda')

# # model.set_generation_params(duration=60)

# # model.lm.load_state_dict(torch.load('lm_final.pt'))

# # res = model.generate([
# #     'Drake type rap beat'
# # ],
# #     progress=True)
# # display_audio(res, 32000)


# # # !pip install --upgrade --no-cache-dir gdown

# # # !gdown 1apJUdQql8HC2xO6FWCoAJe0Uf0nlnUi7

# # !python3 -m pip install -U git+https://github.com/facebookresearch/audiocraft#egg=audiocraft

# # !pip install wandb pydu

# # !export PYTHONIOENCODING=utf-8

import boto3
import os
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures

ACCESS_ID = 'AKIA2J37CALYF4QESNBO'
ACCESS_KEY = 'ixSMQYkTYr9450PCeNYfVhKBhJLTSSNtNyKr9RmZ'

s3 = boto3.client('s3', aws_access_key_id=ACCESS_ID,
         aws_secret_access_key= ACCESS_KEY)

bucket_name = 'westai'
prefix = 'smaller'  # Optional: If you want to download objects from a specific prefix
local_directory = 'local_directory'  # Replace with your local directory path

def upload_files(path, bucket_name, s3_folder):
    session = boto3.Session(
        aws_access_key_id=ACCESS_ID,
        aws_secret_access_key=ACCESS_KEY,
    )

    s3 = session.resource('s3')
    bucket = s3.Bucket(bucket_name)

    files_to_upload = []
    
    for root, dirs, files in os.walk(path):
        files_to_upload.extend(sorted([os.path.join(root, file) for file in files]))

    for full_path in files_to_upload:
        with open(full_path, 'rb') as data:
            s3_path = os.path.join(s3_folder, os.path.relpath(full_path, path))
            print(s3_path)
            bucket.put_object(Key=s3_path, Body=data)

if __name__ == "__main__":
    upload_files('/Users/zeke/Documents/Github/BoominAI/output', 'westai', 'smaller')
