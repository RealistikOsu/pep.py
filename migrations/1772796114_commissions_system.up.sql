CREATE TABLE IF NOT EXISTS commission_templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    goal INT NOT NULL,
    reward INT NOT NULL
);

INSERT INTO commission_templates (name, description, type, goal, reward) VALUES 
('Grind never stops', 'Play {goal} maps today', 'playcount', 5, 10),
('Wealthy play', 'Gain {goal} total score today', 'total_score', 10000000, 15),
('Sniper', 'Achieve over {goal}% accuracy on any map', 'accuracy', 98, 10),
('Farmer', 'Gain {goal} PP today', 'pp', 10, 20),
('Consistency', 'Play for {goal} minutes today', 'playtime', 15, 15),
('Welcome back', 'Log in to the server', 'login', 1, 5),
('Ranked expansion', 'Gain {goal} ranked score today', 'ranked_score', 5000000, 15),
('Active player', 'Play {goal} maps today', 'playcount', 15, 25),
('Score collector', 'Gain {goal} total score today', 'total_score', 50000000, 30);

CREATE TABLE IF NOT EXISTS user_commissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    goal INT NOT NULL,
    progress INT DEFAULT 0,
    reward INT NOT NULL,
    completed TINYINT(1) DEFAULT 0,
    start_value BIGINT DEFAULT 0,
    date DATE NOT NULL,
    UNIQUE KEY (user_id, name, date),
    INDEX (user_id, date)
);

CREATE TABLE IF NOT EXISTS user_daily_bonus (
    user_id INT NOT NULL,
    date DATE NOT NULL,
    claimed TINYINT(1) DEFAULT 0,
    PRIMARY KEY (user_id, date)
);

CREATE TABLE IF NOT EXISTS user_commission_claims (
    id INT AUTO_INCREMENT PRIMARY KEY,
    commission_id INT NOT NULL UNIQUE
);
