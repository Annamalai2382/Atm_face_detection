CREATE DATABASE atm_app;
USE atm_app;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  account_number VARCHAR(64) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  balance DECIMAL(12,2) DEFAULT 0.00,
  face_registered TINYINT(1) DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transactions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  account_number VARCHAR(64) NOT NULL,
  type ENUM('deposit','withdraw') NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE atm_machine (
  id INT PRIMARY KEY,
  cash_available DECIMAL(12,2) NOT NULL
);

INSERT INTO atm_machine (id, cash_available) VALUES (1, 10000.00);
