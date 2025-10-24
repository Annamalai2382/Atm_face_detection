import os
import cv2
import numpy as np
import json

faces_dir = 'faces'
model_path = os.path.join(faces_dir, 'trainer.yml')
labels_path = os.path.join(faces_dir, 'labels.json')

face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

recognizer = cv2.face.LBPHFaceRecognizer_create()

current_label = 0
label_ids = {}
x_train = []
y_labels = []

for account in os.listdir(faces_dir):
    account_path = os.path.join(faces_dir, account)
    if not os.path.isdir(account_path):
        continue
    label = current_label
    label_ids[str(label)] = account
    for image_name in os.listdir(account_path):
        img_path = os.path.join(account_path, image_name)
        img = cv2.imread(img_path)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_detector.detectMultiScale(gray,1.2,5)
        for (x,y,w,h) in faces:
            roi = gray[y:y+h, x:x+w]
            roi_resized = cv2.resize(roi, (200,200))
            x_train.append(roi_resized)
            y_labels.append(label)
    current_label += 1

if len(x_train) == 0:
    print('No training data found under faces/')
    exit(1)

recognizer.train(x_train, np.array(y_labels))
recognizer.save(model_path)
with open(labels_path, 'w') as f:
    json.dump(label_ids, f)
print('Training complete. Model saved to', model_path)
