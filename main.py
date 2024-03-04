import time
from pathlib import Path
import os
import boto3
from botocore import client
import re
import random
import subprocess
import boto3

from modal import Image, Stub, method, gpu

stub = Stub("jubsterai")

def run_commands(commands):
    try:
        subprocess.run(commands, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")


def download_models():
    start_time = time.time()
    from audiocraft.models import musicgen

    run_commands("AWS_ACCESS_KEY_ID=AKIA2J37CALYGP54WYS7 AWS_SECRET_ACCESS_KEY=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 aws s3 sync s3://jubbamodel/ ./")
    
    global model
    model = musicgen.MusicGen.get_pretrained('facebook/musicgen-medium', device='cuda')
    model.lm.load_state_dict(torch.load('NEW_MODEL.pt'))


    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Script execution time: {execution_time} seconds")



image = (
    Image.debian_slim(python_version="3.9")
    .apt_install("git", "ffmpeg")
    .pip_install(
        "awscli",
        "boto3",
        "spleeter",
        "git+https://github.com/facebookresearch/audiocraft.git",
    )
    .run_commands("ls")
    .run_commands("pwd")
    .run_commands("export PYTHONIOENCODING=utf-8")
    .run_function(download_models, gpu="any")
)
stub.image = image

# Set AWS credentials as environment variables
os.environ['AWS_ACCESS_KEY_ID'] = 'AKIA2J37CALYGP54WYS7'
os.environ['AWS_SECRET_ACCESS_KEY'] = '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'

with image.run_inside():
    import torch


def upload_to_s3(local_file_path, bucket_name, s3_key):
    s3 = boto3.client('s3', aws_access_key_id="AKIA2J37CALYGP54WYS7", aws_secret_access_key="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")
    s3.upload_file(local_file_path, bucket_name, s3_key)


@stub.cls(gpu=gpu.A10G())
class Audiocraft:
    @method()
    def generate(
        self,
        prompt: str,
        duration: int,
        extend_stride: int,
        temperature: float,
    ):
        from audiocraft.data.audio import audio_write

        model.set_generation_params(duration=duration, extend_stride=extend_stride, temperature=temperature)
        prompt = prompt.lower()
        wav = model.generate([prompt], progress=True)

        bucket_name = 'westai'
        s3 = boto3.client('s3', config=client.Config(signature_version='s3v4'))

        final_beat = []
        final_bass = []
        final_drums = []
        final_synths = []

        for idx, one_wav in enumerate(wav):
            prompt_name = re.sub(r'[^\w\s]', '', prompt).replace(" ", "-").lower()
            print(prompt_name)
            file_name = f'{prompt_name}-{random.randint(1, 999999999999999999999)}'
            audio_write(file_name, one_wav.cpu(), model.sample_rate, strategy="loudness")

            local_file_path = f'./{file_name}.wav'

            get_stems = f"spleeter separate -o output -p spleeter:4stems-16kHz {local_file_path}"
            subprocess.run(get_stems, shell=True)

            bass = f"./output/{file_name}/bass.wav"
            drums = f"./output/{file_name}/drums.wav"
            synths = f"./output/{file_name}/other.wav"

            s3_key_bass = f'generated_beatz/{file_name}-bass.wav'
            upload_to_s3(bass, bucket_name, s3_key_bass)
            s3_file_path_bass = s3.generate_presigned_url(ClientMethod='get_object', Params={'Bucket': bucket_name, 'Key': s3_key_bass}, ExpiresIn=3600)
            final_bass.append(s3_file_path_bass)

            s3_key_drums = f'generated_beatz/{file_name}-drums.wav'
            upload_to_s3(drums, bucket_name, s3_key_drums)
            s3_file_path_drums = s3.generate_presigned_url(ClientMethod='get_object', Params={'Bucket': bucket_name, 'Key': s3_key_drums}, ExpiresIn=3600)
            final_drums.append(s3_file_path_drums)

            s3_key_synths = f'generated_beatz/{file_name}-synths.wav'
            upload_to_s3(synths, bucket_name, s3_key_synths)
            s3_file_path_synths = s3.generate_presigned_url(ClientMethod='get_object', Params={'Bucket': bucket_name, 'Key': s3_key_synths}, ExpiresIn=3600)
            final_synths.append(s3_file_path_synths)


            # REMOVE THE VOCALS FROM THE BEAT & UPLOAD
            remove_vocals = f"spleeter separate -o output -p spleeter:2stems-16kHz {local_file_path}"
            subprocess.run(remove_vocals, shell=True)

            #changing the name accompaniment.wav to the actual name
            original_path = f"./output/{file_name}/accompaniment.wav"
            beat_removed_vocal = f"./output/{file_name}/{file_name}.wav"
            os.rename(original_path, beat_removed_vocal)

            s3_key_beat = f'generated_beatz/{file_name}.wav'
            upload_to_s3(beat_removed_vocal, bucket_name, s3_key_beat)
            s3_file_path_beat = s3.generate_presigned_url(ClientMethod='get_object', Params={'Bucket': bucket_name, 'Key': s3_key_beat}, ExpiresIn=3600)
            final_beat.append(s3_file_path_beat)

            full_res = {
                        "full_beat": final_beat[0],
                        "bass": final_bass[0],
                        "drums": final_drums[0],
                        "synths": final_synths[0]
                    }

        print(full_res)
        return full_res


@stub.local_entrypoint()
def main(prompt: str, duration: int, extend_stride: int, temperature: float):

    start_time = time.time()
    
    audiocraft = Audiocraft()
    final_beat = audiocraft.generate.remote(
        prompt=prompt, duration=duration, extend_stride=extend_stride, temperature=temperature
    )

    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Script execution time: {execution_time} seconds")

    return final_beat


