
import torch
import clip
import torch 
from collections import OrderedDict
import math
import timm

def copyStateDict(state_dict):
    if list(state_dict.keys())[0].startswith("module"):
        start_idx = 1
    else:
        start_idx = 0
    new_state_dict = OrderedDict()
    for k, v in state_dict.items():
        name = ".".join(k.split(".")[start_idx:])
        new_state_dict[name] = v
    return new_state_dict

class AudioEncoder(torch.nn.Module):
    def __init__(self, backbone_name="resnet18"):
        super(AudioEncoder, self).__init__()
        self.backbone_name = backbone_name
        self.conv = torch.nn.Conv2d(1, 3, (3, 3))
        self.feature_extractor = timm.create_model(self.backbone_name, num_classes=512, pretrained=False)

    def forward(self, x):
        x = self.conv(x)
        x = self.feature_extractor(x)
        return x

class SoundCLIPLoss(torch.nn.Module):

    def __init__(self, opts):
        super(SoundCLIPLoss, self).__init__()
        self.model, self.preprocess = clip.load("ViT-B/32", device="cuda")
        self.upsample = torch.nn.Upsample(scale_factor=7)
        self.avg_pool = torch.nn.AvgPool2d(kernel_size=opts.stylegan_size // 32)

        self.audio_encoder = AudioEncoder()
        
        self.audio_encoder.load_state_dict(copyStateDict(torch.load("../pretrained_models/resnet18.pth")))
        
        self.audio_encoder = self.audio_encoder.cuda()
        self.audio_encoder.eval()

    def forward(self, image, audio):
        image = self.avg_pool(self.upsample(image))
        image_features = self.model.encode_image(image).float()
        audio_features = self.audio_encoder(audio).float()

        audio_features = audio_features / audio_features.norm(dim=-1, keepdim=True)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        sim = (image_features @ audio_features.T)[0] * math.exp(0.07)
        loss = 1 - sim
        return loss

class SoundCLIPCLAPLoss(torch.nn.Module):

    def __init__(self, opts):
        super(SoundCLIPCLAPLoss, self).__init__()
        print('Loading SoundCLIPCLAPLoss')
        self.model, self.preprocess = clip.load("ViT-B/32", device="cuda")
        self.upsample = torch.nn.Upsample(scale_factor=7)
        self.avg_pool = torch.nn.AvgPool2d(kernel_size=opts.stylegan_size // 32)
    def forward(self, image, audio):
        image = self.avg_pool(self.upsample(image))
        image_features = self.model.encode_image(image).float()
        audio_features = audio.squeeze(0)
        audio_features = audio_features / audio_features.norm(dim=-1, keepdim=True)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        sim = (image_features @ audio_features.T)[0] * math.exp(0.07)
        loss = 1 - sim
        return loss