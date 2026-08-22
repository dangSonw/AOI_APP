import os
import cv2
import numpy as np

from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

TRAIN_DIR = "cat-and-dog/training_set"
TEST_DIR = "cat-and-dog/test_set"

IMAGE_SIZE = (128, 128)

CLASS_NAMES = {
    "cats": 0,
    "dogs": 1
}

hog = cv2.HOGDescriptor(
    _winSize=(128, 128),
    _blockSize=(16, 16),
    _blockStride=(8, 8),
    _cellSize=(8, 8),
    _nbins=9
)

def extract_hog(image_path):
    image = cv2.imread(image_path)
    if image is None:
        return None
    image = cv2.resize(image, IMAGE_SIZE)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    feature = hog.compute(gray)
    feature = feature.flatten()
    return feature

def load_dataset(root_dir):
    X = []
    y = []

    for class_name, label in CLASS_NAMES.items():
        class_dir = os.path.join(root_dir, class_name)
        print(f"Loading: {class_dir}")
        for filename in os.listdir(class_dir):
            file_path = os.path.join(class_dir, filename)
            if not filename.lower().endswith(
                (".jpg", ".jpeg", ".png", ".bmp")
            ):
                continue
            feature = extract_hog(file_path)
            if feature is not None:
                X.append(feature)
                y.append(label)

    return np.array(X), np.array(y)

print("Loading training data...")
X_train, y_train = load_dataset(TRAIN_DIR)
print("Loading test data...")
X_test, y_test = load_dataset(TEST_DIR)
print()
print("X_train:", X_train.shape)
print("y_train:", y_train.shape)
print("X_test:", X_test.shape)
print("y_test:", y_test.shape)

model = Pipeline([
    ("scaler", StandardScaler()),
    ("svm", SVC(
        kernel="rbf",
        C=10,
        gamma="scale"
    ))
])

print("\nTraining SVM...")
model.fit(X_train, y_train)
print("Training completed.")
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print("\nAccuracy:")
print(accuracy)
print("\nClassification Report:")
print(
    classification_report(
        y_test,
        y_pred,
        target_names=["Cat", "Dog"]
    )
)
print("\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))