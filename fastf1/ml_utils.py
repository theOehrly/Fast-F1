import numpy as np
import torch.nn as nn
import torch
import fastf1
def create_sliding_window(telemetry_df, window_size=50, features=['Speed', 'Throttle', 'Brake', 'RPM']):
    df = telemetry_df[features].copy() 
    df['Speed'] /= 340.0
    df['Throttle'] /= 100.0
    df['RPM'] /= 15000.0 
    if 'Brake' in features:
        df['Brake'] = df['Brake'].astype(float)      
    values = df.values
    sequences = []
    for i in range(len(values) - window_size):
        sequences.append(values[i : i + window_size])
    return torch.tensor(np.array(sequences), dtype=torch.float32)
class F1predictor(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers, output_dim):
        super(F1predictor, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.gru = nn.GRU(input_dim, hidden_dim, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_dim, output_dim)
    def forward(self, x):
        out, _ = self.gru(x)
        out = self.fc(out[:, -1, :]) 
        return out
fastf1.Cache.enable_cache('cache')
session = fastf1.get_session(2024, 'Austrian Grand Prix', 'R')
session.load()
fastest_lap = session.laps.pick_drivers('VER').pick_fastest()
telemetry = fastest_lap.get_telemetry().interpolate()
model = F1predictor(input_dim=4, hidden_dim=64, num_layers=2, output_dim=1)
device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")
model.to(device)
X = create_sliding_window(telemetry, features=['Speed', 'Throttle', 'Brake', 'RPM'])
X = X.to(device)
print(f"Device: {X.device}")
print(f"Input Tensor Shape: {X.shape}") 
