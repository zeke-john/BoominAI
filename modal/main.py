import os
import random
import re
import subprocess
import boto3
from botocore import client
from multiprocessing import Process
import time
from modal import Image, Stub, method, enter, web_endpoint, Volume

os.environ['AWS_ACCESS_KEY_ID'] = 'AKIA2J37CALYGP54WYS7'
os.environ['AWS_SECRET_ACCESS_KEY'] = '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'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

stub = Stub("JubsterAI")

# WARNING[XFORMERS]: xFormers can't load C++/CUDA extensions. xFormers was built for:
#     PyTorch 2.1.0+cu121 with CUDA 1201 (you have 2.4.0.dev20240319+cu121)
#     Python  3.9.18 (you have 3.9.18)
#   Please reinstall xformers (see https://github.com/facebookresearch/xformers#installing-xformers)
#   Memory-efficient attention, SwiGLU, sparse and more won't be available.
#   Set XFORMERS_MORE_DETAILS=1 for more details
# 2024-03-19 22:54:28.837492: I tensorflow/core/platform/cpu_feature_guard.cc:210] This TensorFlow binary is optimized to use available CPU instructions in performance-critical operations.
# To enable the following instructions: AVX2 AVX512F AVX512_VNNI AVX512_BF16 AVX512_FP16 AVX_VNNI AMX_TILE AMX_INT8 AMX_BF16 FMA, in other operations, rebuild TensorFlow with the appropriate compiler flags.
# 2024-03-19 22:54:30.049070: W tensorflow/compiler/tf2tensorrt/utils/py_utils.cc:38] TF-TRT Warning: Could not find TensorRT

# => Step 3: RUN find / -name 'libcudart.so*'
# /usr/local/lib/python3.9/site-packages/nvidia/cuda_runtime/lib/libcudart.so.12

image = (
    Image.debian_slim(python_version="3.9.18").conda()
    .apt_install("git", "ffmpeg", "libssl-dev")
    .pip_install("boto3", "spleeter", "git+https://github.com/facebookresearch/audiocraft.git", "lmdb")
    .run_commands
        (
            "python -m pip install -U tensorflow[and-cuda]", 
            "pip install torch==2.1.0+cu121 --index-url https://download.pytorch.org/whl/cu121",
            "nvidia-smi", 
            "find / -name 'libcudart.so*'", 
            "export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib/python3.9/site-packages/nvidia/cuda_runtime/lib/libcudart.so.12", 
            gpu="H100"
        )
    .conda_install("cudatoolkit", "cudnn", channels=["conda-forge"], gpu="H100")
    )


stub.image = image

with image.imports():
    from audiocraft.models import MusicGen
    from audiocraft.data.audio import audio_write    
    import torch

@stub.cls(gpu='A100', timeout=600, volumes={"/my_vol": Volume.from_name("musicgen")})
class Audiocraft:
    @enter()
    def get_model(self):
        print('Getting model')
        start_time = time.time()

        self.model = MusicGen.get_pretrained('facebook/musicgen-medium', device='cuda')
        self.model.lm.load_state_dict(torch.load('/my_vol/NEW_MODEL.pt', map_location=torch.device('cuda')))

        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f'Model gotten after {elapsed_time}')

    def upload_to_s3(self, local_file_path, bucket_name, s3_key):
        s3 = boto3.client('s3', config=client.Config(signature_version='s3v4'))
        s3.upload_file(local_file_path, bucket_name, s3_key)

    def remove_vocals(self, local_file_path, file_name):
        with torch.no_grad():
            with torch.backends.cuda.sdp_kernel(enable_flash=True, enable_math=False, enable_mem_efficient=False):
                remove_vocals = f"spleeter separate -o output -p spleeter:2stems-16kHz {local_file_path}"
                subprocess.run(remove_vocals, shell=True)

        original_path = f"./output/{file_name}/accompaniment.wav"
        beat_removed_vocal = f"./output/{file_name}/{file_name}.wav"
        os.rename(original_path, beat_removed_vocal)

    @method()
    def generate(self, prompt: str, duration: int, extend_stride: int, temperature: float):
        prompt = prompt.lower()
        s3 = boto3.client('s3', config=client.Config(signature_version='s3v4'))

        print('AHHH generating')
        start_time = time.time()

        with torch.backends.cuda.sdp_kernel(enable_flash=True, enable_math=False, enable_mem_efficient=False):
            self.model.set_generation_params(duration=duration, extend_stride=extend_stride, temperature=temperature)
            wav = self.model.generate([prompt], progress=True)

        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Generation time: {elapsed_time} seconds")
        print('Done generating')

        bucket_name = 'westai'
        final_beat = []
        final_bass = []
        final_drums = []
        final_synths = []

        for idx, one_wav in enumerate(wav):
            prompt_name = re.sub(r'[^\w\s]', '', prompt).replace(" ", "-").lower()
            file_name = f'{prompt_name}-{random.randint(1, 999999999999999999999999999999999999999999999)}'
            audio_write(file_name, one_wav.cpu(), self.model.sample_rate, strategy="loudness")
            local_file_path = f'./{file_name}.wav'

            remove_vocals_process = Process(target=self.remove_vocals, args=(local_file_path, file_name))
            remove_vocals_process.start()

            with torch.no_grad():
                with torch.backends.cuda.sdp_kernel(enable_flash=True, enable_math=False, enable_mem_efficient=False):
                    get_stems = f"spleeter separate -o output -p spleeter:4stems-16kHz {local_file_path}"
                    subprocess.run(get_stems, shell=True)

            stems = ['bass', 'drums', 'other']
            for stem in stems:
                stem_path = f"./output/{file_name}/{stem}.wav"
                s3_key_stem = f'generated_beatz/{file_name}-{stem}.wav'
                self.upload_to_s3(stem_path, bucket_name, s3_key_stem)
                s3_file_path = s3.generate_presigned_url(ClientMethod='get_object', Params={'Bucket': bucket_name, 'Key': s3_key_stem}, ExpiresIn=3600)
                if stem == 'bass':
                    final_bass.append(s3_file_path)
                elif stem == 'drums':
                    final_drums.append(s3_file_path)
                else:
                    final_synths.append(s3_file_path)

            remove_vocals_process.join()

            beat_removed_vocal_path = f"./output/{file_name}/{file_name}.wav"
            s3_key = f'generated_beatz/{file_name}.wav'
            self.upload_to_s3(beat_removed_vocal_path, bucket_name, s3_key)
            s3_file_path = s3.generate_presigned_url(ClientMethod='get_object', Params={'Bucket': bucket_name, 'Key': s3_key}, ExpiresIn=3600)
            final_beat.append(s3_file_path)

        full_res = {"full_beat": final_beat[0], "bass": final_bass[0], "drums": final_drums[0], "synths": final_synths[0]}
        return full_res

@stub.function(timeout=600, volumes={"/my_vol": Volume.from_name("musicgen")})
@web_endpoint()
def main(prompt: str, duration: int, extend_stride: int, temperature: float):
    audiocraft = Audiocraft()
    final_beat = audiocraft.generate.remote(prompt=prompt, duration=duration, extend_stride=extend_stride, temperature=temperature)
    print(final_beat)
    return final_beat

