# ATM Webapp (Flask + OpenCV LBPH + MySQL)

1. Create MySQL database using `schema.sql` (open in MySQL Workbench and run).
2. Update DB credentials in `app.py` DB_CONFIG.
3. Create a virtualenv and install requirements: `pip install -r requirements.txt`.
4. Run the Flask app: `python app.py`.
5. Register a user at `/register` (account_number + password).
6. Use the Register page's face panel to capture a few face images for that account -> click Upload.
7. Run `python train_faces.py` to produce `faces/trainer.yml` + `faces/labels.json`.
8. Use `/login` (password) or face login using the camera.
9. Admin: visit `/admin/login` and use `admin` / `admin123` to login and refill ATM or view transactions.

Notes:
- We use LBPH recognizer to avoid dlib. Tweak thresholds as needed.
- For production: use HTTPS, stronger secrets, store admin hashed creds, improve face dataset, secure file uploads.
