from datetime import datetime, timezone
from pathlib import Path
import time

import joblib
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

print("training job started")
for step in range(1, 7):
    print(f"progress {step}/6")
    time.sleep(5)

X, y = load_iris(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model = LogisticRegression(max_iter=300)
model.fit(X_train, y_train)
predictions = model.predict(X_test)
accuracy = accuracy_score(y_test, predictions)

models_dir = Path("/models")
models_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
model_path = models_dir / f"model-{timestamp}.pkl"
joblib.dump(model, model_path)

# ponytail: single metric keeps artifact workflow clear without training complexity
print(f"accuracy={accuracy:.4f}")
print(f"saved_model={model_path}")
