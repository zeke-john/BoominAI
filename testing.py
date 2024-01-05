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

def download_file(bucket, object_name, local_path):
    s3.download_file(bucket, object_name, local_path)

def list_and_download_objects(bucket, prefix, local_directory):
    kwargs = {'Bucket': bucket, 'Prefix': prefix}

    objects = []
    while True:
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp.get('Contents', []):
            objects.append(obj['Key'])
        if 'NextContinuationToken' not in resp:
            break
        kwargs['ContinuationToken'] = resp['NextContinuationToken']

    with ThreadPoolExecutor(max_workers=50) as executor:  # Adjust max_workers as needed
        future_to_key = {executor.submit(download_file, bucket, key, os.path.join(local_directory, key)): key for key in objects}
        for future in concurrent.futures.as_completed(future_to_key):
            key = future_to_key[future]
            try:
                future.result()
            except Exception as exc:
                print(f'{key} generated an exception: {exc}')

list_and_download_objects(bucket_name, prefix, local_directory)

