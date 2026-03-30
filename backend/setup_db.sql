-- ══════════════════════════════════════════════════
--  Herambha Portfolio — MySQL Database Setup
--  Run this file once to create all tables
--  Command: mysql -u root -p < setup_db.sql
-- ══════════════════════════════════════════════════

-- Create database
--CREATE DATABASE IF NOT EXISTS herambha_portfolio;
USE railway;

-- ── PROJECTS ──
CREATE TABLE IF NOT EXISTS projects (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    title         VARCHAR(255)  NOT NULL,
    description   TEXT,
    tech          TEXT,
    image_url     VARCHAR(500),
    project_link  VARCHAR(500),
    emoji         VARCHAR(10)   DEFAULT '🤖',
    created_at    TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

-- ── SKILL CATEGORIES ──
CREATE TABLE IF NOT EXISTS skill_categories (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    sort_order  INT          DEFAULT 0
);

-- ── INDIVIDUAL SKILLS ──
CREATE TABLE IF NOT EXISTS skills (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    category_id  INT,
    FOREIGN KEY (category_id) REFERENCES skill_categories(id) ON DELETE CASCADE
);

-- ── CERTIFICATIONS ──
CREATE TABLE IF NOT EXISTS certifications (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    title            VARCHAR(255) NOT NULL,
    issuer           VARCHAR(255),
    type             VARCHAR(50)  DEFAULT 'Course',
    date_completed   VARCHAR(50),
    credential_link  VARCHAR(500),
    emoji            VARCHAR(10),
    created_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- ── CONTACT MESSAGES ──
CREATE TABLE IF NOT EXISTS messages (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(255),
    email       VARCHAR(255),
    subject     VARCHAR(255),
    message     TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ══════════════════════════════════════════════════
--  DEFAULT DATA — Herambha's real data pre-loaded
-- ══════════════════════════════════════════════════

-- Default Projects
INSERT INTO projects (title, description, tech, image_url, project_link, emoji) VALUES
('Face Recognition System',
 'Real-time SVM-based face recognition via webcam. End-to-end: image collection, 128-D encoding, SVM training, Flask REST API, and live browser display.',
 'Python,OpenCV,SVM,Flask,Pickle,face_recognition', '', 'https://github.com/Herambha1226/', '🎭'),

('Handwritten Digit Recognition',
 'KNN classifier on MNIST (70,000 images) with real-time webcam digit recognition. Full preprocessing pipeline and text-to-speech via pyttsx3.',
 'Python,KNN,OpenCV,MNIST,pyttsx3,Matplotlib', '', 'https://github.com/Herambha1226/', '✍️'),

('Herambha – Desktop Messenger',
 'Full-stack desktop messaging app with email OTP auth. Packaged as Windows .exe via PyInstaller. Flask REST API deployed on Render with KivyMD multi-screen UI.',
 'Python,Flask,KivyMD,PyInstaller,Render,Firebase', '', 'https://github.com/Herambha1226/', '💬'),

('Admission Predictor',
 'Logistic Regression binary classifier predicting student admission outcomes with decision boundary visualisation and CLI prediction interface.',
 'Python,Logistic Regression,Pandas,Matplotlib,Seaborn,Joblib', '', 'https://github.com/Herambha1226/', '📊');

-- Default Skill Categories
INSERT INTO skill_categories (name, sort_order) VALUES
('Languages & ML Algorithms', 1),
('ML Libraries', 2),
('Computer Vision & Web', 3),
('Desktop · Database · Cloud', 4);

-- Default Skills
INSERT INTO skills (name, category_id) VALUES
('Python', 1), ('SVM', 1), ('KNN', 1), ('Logistic Regression', 1),
('Scikit-Learn', 2), ('NumPy', 2), ('Pandas', 2), ('Matplotlib', 2), ('Seaborn', 2), ('face_recognition', 2),
('OpenCV', 3), ('Flask', 3), ('REST API', 3), ('HTML', 3), ('CSS', 3),
('KivyMD', 4), ('PyInstaller', 4), ('MySQL', 4), ('Firebase', 4),
('Render', 4), ('Git', 4), ('GitHub', 4), ('Pickle', 4), ('Joblib', 4), ('pyttsx3', 4);

-- Confirm setup
SELECT 'Database setup complete!' AS Status;
SELECT COUNT(*) AS projects_count  FROM projects;
SELECT COUNT(*) AS skills_count    FROM skills;
