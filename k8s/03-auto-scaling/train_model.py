from joblib import dump
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression


def main() -> None:
    iris = load_iris()
    model = LogisticRegression(max_iter=300)
    model.fit(iris.data, iris.target)
    dump(model, "model.pkl")
    # ponytail: keep same tiny artifact pattern across labs for consistency
    print("Saved model.pkl")


if __name__ == "__main__":
    main()
