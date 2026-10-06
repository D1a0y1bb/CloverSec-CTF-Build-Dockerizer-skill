CREATE DATABASE IF NOT EXISTS ctf;
CREATE TABLE IF NOT EXISTS ctf.healthcheck (
  id INT PRIMARY KEY AUTO_INCREMENT,
  message VARCHAR(255) NOT NULL
);
INSERT INTO ctf.healthcheck(message) VALUES ('lamp-basic-ready');
