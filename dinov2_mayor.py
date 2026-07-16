import torch
model = torch.hub.load(
    "facebookresearch/dinov2",
    "dinov2_vitb14"
)
print(model)
print(torch.__version__)