from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd
import torch
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


class FraudNet(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, dropout: float) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.BatchNorm1d(hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.network(inputs)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train fraud detection model with SageMaker script mode")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch_size", type=int, default=128)
    parser.add_argument("--learning_rate", type=float, default=1e-3)
    parser.add_argument("--dropout", type=float, default=0.2)
    parser.add_argument("--hidden_dim", type=int, default=128)
    return parser


def _load_channel_csv(channel_path: str) -> tuple[torch.Tensor, torch.Tensor]:
    csv_files = sorted(Path(channel_path).glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in channel path: {channel_path}")

    dataframe = pd.read_csv(csv_files[0])
    features = dataframe.drop(columns=["Class"]).to_numpy(dtype="float32")
    labels = dataframe["Class"].to_numpy(dtype="float32")
    feature_tensor = torch.tensor(features, dtype=torch.float32)
    label_tensor = torch.tensor(labels, dtype=torch.float32).unsqueeze(1)
    return feature_tensor, label_tensor


def _make_loader(features: torch.Tensor, labels: torch.Tensor, batch_size: int, shuffle: bool) -> DataLoader:
    dataset = TensorDataset(features, labels)
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)


def _evaluate(model: FraudNet, data_loader: DataLoader, device: torch.device) -> dict[str, float]:
    model.eval()
    all_predictions: list[int] = []
    all_labels: list[int] = []

    with torch.no_grad():
        for batch_features, batch_labels in data_loader:
            logits = model(batch_features.to(device)).squeeze(1)
            probabilities = torch.sigmoid(logits)
            predictions = (probabilities >= 0.5).int().cpu().tolist()
            labels = batch_labels.squeeze(1).int().cpu().tolist()
            all_predictions.extend(predictions)
            all_labels.extend(labels)

    metrics = {
        "accuracy": float(accuracy_score(all_labels, all_predictions)),
        "precision": float(precision_score(all_labels, all_predictions, zero_division=0)),
        "recall": float(recall_score(all_labels, all_predictions, zero_division=0)),
        "f1": float(f1_score(all_labels, all_predictions, zero_division=0)),
    }
    return metrics


def main() -> int:
    args = _build_parser().parse_args()

    train_channel = os.environ["SM_CHANNEL_TRAIN"]
    validation_channel = os.environ["SM_CHANNEL_VALIDATION"]
    model_dir = os.environ["SM_MODEL_DIR"]

    train_features, train_labels = _load_channel_csv(train_channel)
    validation_features, validation_labels = _load_channel_csv(validation_channel)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = FraudNet(input_dim=train_features.shape[1], hidden_dim=args.hidden_dim, dropout=args.dropout).to(device)

    positive_count = float((train_labels == 1.0).sum().item())
    negative_count = float((train_labels == 0.0).sum().item())
    pos_weight_value = negative_count / max(positive_count, 1.0)
    pos_weight = torch.tensor([pos_weight_value], dtype=torch.float32, device=device)

    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)

    train_loader = _make_loader(train_features, train_labels, args.batch_size, shuffle=True)
    validation_loader = _make_loader(validation_features, validation_labels, args.batch_size, shuffle=False)

    for epoch in range(1, args.epochs + 1):
        model.train()
        epoch_loss = 0.0
        for batch_features, batch_labels in train_loader:
            optimizer.zero_grad()
            logits = model(batch_features.to(device))
            loss = criterion(logits, batch_labels.to(device))
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()

        mean_loss = epoch_loss / max(len(train_loader), 1)
        validation_metrics = _evaluate(model, validation_loader, device)
        print(
            " ".join(
                [
                    f"epoch={epoch}",
                    f"train:loss={mean_loss:.6f}",
                    f"validation:accuracy={validation_metrics['accuracy']:.6f}",
                    f"validation:precision={validation_metrics['precision']:.6f}",
                    f"validation:recall={validation_metrics['recall']:.6f}",
                    f"validation:f1={validation_metrics['f1']:.6f}",
                ]
            )
        )

    model_path = Path(model_dir) / "model.pth"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "input_dim": int(train_features.shape[1]),
            "hidden_dim": int(args.hidden_dim),
            "dropout": float(args.dropout),
        },
        model_path,
    )

    final_metrics = _evaluate(model, validation_loader, device)
    metrics_path = Path(model_dir) / "metrics.json"
    metrics_path.write_text(json.dumps(final_metrics, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
