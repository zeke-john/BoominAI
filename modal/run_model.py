!python3 -m pip install -U git+https://github.com/facebookresearch/audiocraft.git
!pip install boto3 openvino awscli
!pip install awscli --force-reinstall --upgrade
!python3 -m pip install spleeter

!export PYTHONIOENCODING=utf-8

!apt-get update && apt-get install -y ffmpeg
!AWS_ACCESS_KEY_ID=AKIA2J37CALYGP54WYS7 AWS_SECRET_ACCESS_KEY=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 aws s3 sync s3://jubbamodel/ ./

from audiocraft.data.audio import audio_write
from audiocraft.models import musicgen
import torch
import random
import spleeter
import subprocess
import os
import boto3
from botocore import client
import re
import openvino.frontend.pytorch.torchdynamo.backend
import torch

os.environ['AWS_ACCESS_KEY_ID'] = 'AKIA2J37CALYGP54WYS7'
os.environ['AWS_SECRET_ACCESS_KEY'] = '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'
os.environ["OPENVINO_TORCH_BACKEND_DEVICE"] = "GPU"
os.environ["PYTORCH_TRACING_MODE"] = "TORCHFX"
os.environ["OPENVINO_DEVICE"] = "GPU"
os.environ["TORCH_LOGS"] = "+dynamo"
os.environ["TORCHDYNAMO_VERBOSE"] = "1"

torch._dynamo.config.suppress_errors = True

model = musicgen.MusicGen.get_pretrained('facebook/musicgen-medium', device='cuda')
model.lm.load_state_dict(torch.load('NEW_MODEL.pt'))
model._generate_tokens = torch.compile(model._generate_tokens, backend="openvino")

def upload_to_s3(local_file_path, bucket_name, s3_key):
	s3 = boto3.client('s3', aws_access_key_id="AKIA2J37CALYGP54WYS7", aws_secret_access_key="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")
	s3.upload_file(local_file_path, bucket_name, s3_key)


def process_input(input, duration, extend_stride, temperature):
	prompt = input.lower()

	with torch.backends.cuda.sdp_kernel(enable_flash=True, enable_math=False, enable_mem_efficient=False):
		model.set_generation_params(duration=duration, extend_stride=extend_stride, temperature=temperature)
		wav = model.generate([prompt], progress=True)


	bucket_name = 'westai'
	s3 = boto3.client('s3', config=client.Config(signature_version='s3v4'))

	final_beat = []
	final_bass = []
	final_drums = []
	final_synths = []

	for idx, one_wav in enumerate(wav):
		prompt_name = re.sub(r'[^\w\s]', '', prompt).replace(" ", "-").lower()
		file_name = f'{prompt_name}-{random.randint(1, 999999999999999999999999999999999999999999)}'
		audio_write(file_name, one_wav.cpu(), self.model.sample_rate, strategy="loudness")
		local_file_path = f'./{file_name}.wav'

		with torch.backends.cuda.sdp_kernel(enable_flash=True, enable_math=False, enable_mem_efficient=False):
			get_stems = f"spleeter separate -o output -p spleeter:4stems-16kHz {local_file_path}"
			subprocess.run(get_stems, shell=True)

		stems = ['bass', 'drums', 'other']
		for stem in stems:
			stem_path = f"./output/{file_name}/{stem}.wav"
			s3_key = f'generated_beatz/{file_name}-{stem}.wav'
			upload_to_s3(stem_path, bucket_name, s3_key)
			s3_file_path = s3.generate_presigned_url(ClientMethod='get_object', Params={'Bucket': bucket_name, 'Key': s3_key}, ExpiresIn=3600)
			if stem == 'bass':
				final_bass.append(s3_file_path)
			elif stem == 'drums':
				final_drums.append(s3_file_path)
			else:
				final_synths.append(s3_file_path)

		# Remove vocals
		with torch.backends.cuda.sdp_kernel(enable_flash=True, enable_math=False, enable_mem_efficient=False):
			remove_vocals = f"spleeter separate -o output -p spleeter:2stems-16kHz {local_file_path}"
			subprocess.run(remove_vocals, shell=True)

		original_path = f"./output/{file_name}/accompaniment.wav"
		beat_removed_vocal = f"./output/{file_name}/{file_name}.wav"
		os.rename(original_path, beat_removed_vocal)

		s3_key = f'generated_beatz/{file_name}.wav'
		upload_to_s3(beat_removed_vocal, bucket_name, s3_key)
		s3_file_path = s3.generate_presigned_url(ClientMethod='get_object', Params={'Bucket': bucket_name, 'Key': s3_key}, ExpiresIn=3600)
		final_beat.append(s3_file_path)

	full_res = {"full_beat": final_beat[0], "bass": final_bass[0], "drums": final_drums[0], "synths": final_synths[0]}
	return full_res


process_input('type beat', duration=120, extend_stride=14, temperature=0.75)