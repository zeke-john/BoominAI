
# # # !pip install --upgrade --no-cache-dir gdown

# # # !gdown 1apJUdQql8HC2xO6FWCoAJe0Uf0nlnUi7

# # !python3 -m pip install -U git+https://github.com/facebookresearch/audiocraft#egg=audiocraft

# # !pip install wandb pydu

# !export PYTHONIOENCODING=utf-8

from audiocraft.models import musicgen
from audiocraft.utils.notebook import display_audio
import torch

model = musicgen.MusicGen.get_pretrained('medium', device='cuda')

model.set_generation_params(duration=60)

model.lm.load_state_dict(torch.load('lm_final.pt'))

res = model.generate([
    'Drake type rap beat'
],
    progress=True)
display_audio(res, 32000)

