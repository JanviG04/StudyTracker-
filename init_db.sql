CREATE DATABASE IF NOT EXISTS study_tracker;

USE study_tracker;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS study_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    subject VARCHAR(50),
    hours FLOAT,
    mood VARCHAR(30),
    session_date DATE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);