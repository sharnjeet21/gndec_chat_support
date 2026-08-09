-- PostgreSQL Initialization Schema for tech_support_ai

CREATE TABLE IF NOT EXISTS chat_sessions (
    phone VARCHAR(50) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(50) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_servers (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(50) NOT NULL,
    server_ip VARCHAR(50) NOT NULL,
    ssh_user VARCHAR(100) NOT NULL,
    ssh_password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
