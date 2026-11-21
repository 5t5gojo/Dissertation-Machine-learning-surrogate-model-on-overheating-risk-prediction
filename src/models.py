"""The three surrogate families: Random Forest, XGBoost and a multi-output MLP.

Tree models fit one regressor per target; the MLP predicts all five targets jointly from
standardised inputs and outputs. Everything runs single-threaded with fixed seeds.
"""

from __future__ import annotations

import copy

import numpy as np
import torch
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from torch import nn
from xgboost import XGBRegressor

from common import FEATURES, TARGETS

FAMILIES = ("RF", "XGBoost", "MLP")
PATIENCE = 30  # epochs without validation improvement before early stopping


class MLP(nn.Module):
    """Fully connected network; batch norm, ReLU and dropout between hidden layers."""

    def __init__(self, hidden: list[int], dropout: float):
        super().__init__()
        layers, width = [], len(FEATURES)
        for i, size in enumerate(hidden):
            layers.append(nn.Linear(width, size))
            if i < len(hidden) - 1:
                layers += [nn.BatchNorm1d(size), nn.ReLU(), nn.Dropout(dropout)]
            else:
                layers.append(nn.ReLU())
            width = size
        layers.append(nn.Linear(width, len(TARGETS)))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def fit_model(family: str, config: dict, x, y, x_val, y_val, seed: int, epochs: int) -> tuple[dict, list[dict]]:
    """Fit one candidate configuration. Returns the fitted bundle and the MLP loss curve."""
    if family in ("RF", "XGBoost"):
        if family == "RF":
            estimator, extra = RandomForestRegressor, {}
        else:
            estimator, extra = XGBRegressor, {"objective": "reg:squarederror", "verbosity": 0}
        models = [
            estimator(**config, **extra, random_state=seed, n_jobs=1).fit(x, y[:, i]) for i in range(len(TARGETS))
        ]
        return {"family": family, "models": models}, []
    return fit_mlp(config, x, y, x_val, y_val, seed, epochs)


def fit_mlp(config: dict, x, y, x_val, y_val, seed: int, epochs: int) -> tuple[dict, list[dict]]:
    """Adam with plateau learning-rate decay; keep the weights with the lowest validation loss."""
    torch.set_num_threads(1)
    torch.manual_seed(seed)
    x_scaler, y_scaler = StandardScaler().fit(x), StandardScaler().fit(y)

    def tensor(values):
        return torch.tensor(values, dtype=torch.float32)

    x_train, y_train = tensor(x_scaler.transform(x)), tensor(y_scaler.transform(y))
    x_val, y_val = tensor(x_scaler.transform(x_val)), tensor(y_scaler.transform(y_val))

    model = MLP(config["hidden"], config["dropout"])
    optimizer = torch.optim.Adam(model.parameters(), lr=config["lr"], weight_decay=config["weight_decay"])
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10, factor=0.5, min_lr=1e-5)
    best_loss, waited, best_state, curve = np.inf, 0, None, []
    for epoch in range(1, epochs + 1):
        model.train()
        batch_losses = []
        for batch in torch.randperm(len(x_train)).split(config["batch_size"]):
            if len(batch) < 2:  # batch norm needs at least two rows
                continue
            optimizer.zero_grad()
            loss = nn.functional.mse_loss(model(x_train[batch]), y_train[batch])
            loss.backward()
            optimizer.step()
            batch_losses.append((loss.item(), len(batch)))
        model.eval()
        with torch.no_grad():
            val_loss = nn.functional.mse_loss(model(x_val), y_val).item()
        scheduler.step(val_loss)
        train_loss = sum(loss * n for loss, n in batch_losses) / sum(n for _, n in batch_losses)
        curve.append({"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss})
        if val_loss < best_loss - 1e-6:
            best_loss, waited, best_state = val_loss, 0, copy.deepcopy(model.state_dict())
        else:
            waited += 1
            if waited >= PATIENCE:
                break
    model.load_state_dict(best_state)
    model.eval()
    return {"family": "MLP", "model": model, "x_scaler": x_scaler, "y_scaler": y_scaler}, curve


def predict(bundle: dict, x) -> np.ndarray:
    """Predictions for all five targets, in original units (n_rows x 5)."""
    if bundle["family"] != "MLP":
        return np.column_stack([model.predict(x) for model in bundle["models"]])
    with torch.no_grad():
        scaled = bundle["model"](torch.tensor(bundle["x_scaler"].transform(x), dtype=torch.float32)).numpy()
    return bundle["y_scaler"].inverse_transform(scaled)
