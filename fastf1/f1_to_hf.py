import fastf1
from safetensors.torch import save_file
import torch
import pandas as pd
import numpy as np
fastf1.Cache.enable_cache('cache')
def get_telemetry(year,gp,driver):
    sessions=fastf1.get_session(year,gp,'R')
    sessions.load()
    fastest_lap=sessions.laps.pick_drivers(driver).pick_fastest()
    telemetry = fastest_lap.get_telemetry().interpolate() 
    data_dict={"speed": torch.tensor(telemetry['Speed'].values, dtype=torch.float32),
        "throttle": torch.tensor(telemetry['Throttle'].values, dtype=torch.float32),
        "brake": torch.tensor(telemetry['Brake'].values, dtype=torch.float32),
        "rpm": torch.tensor(telemetry['RPM'].values.astype(float), dtype=torch.float32)}
    return data_dict
tensors=get_telemetry(2024,'Austrian Grand Prix','VER')
save_file(tensors,'VER_AUSTRIAN_GRAND_PRIX.safetensors')
print("Successfully exported F1 telemetry to Safetensors format!")
print(tensors.keys())