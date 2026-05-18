-- Create Database
CREATE DATABASE document_rag_db;

-- Users Table
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Documents Table (Top Level)
CREATE TABLE documents (
    doc_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    content_type VARCHAR(50),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Document Sections (Hierarchical Level 1)
CREATE TABLE document_sections (
    section_id SERIAL PRIMARY KEY,
    doc_id INT NOT NULL,
    section_number INT,
    section_title VARCHAR(500),
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);

-- Document Chunks (Hierarchical Level 2)
CREATE TABLE document_chunks (
    chunk_id SERIAL PRIMARY KEY,
    doc_id INT NOT NULL,
    section_id INT,
    chunk_number INT,
    chunk_text TEXT NOT NULL,
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
    FOREIGN KEY (section_id) REFERENCES document_sections(section_id) ON DELETE SET NULL
);

-- Embeddings Table (Vector data for chunks)
CREATE TABLE chunk_embeddings (
    embedding_id SERIAL PRIMARY KEY,
    chunk_id INT NOT NULL UNIQUE,
    embedding BYTEA NOT NULL,
    FOREIGN KEY (chunk_id) REFERENCES document_chunks(chunk_id) ON DELETE CASCADE
);

-- Conversations Table
CREATE TABLE conversations (
    conversation_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    doc_id INT,
    title VARCHAR(255),
    last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);

-- Chat Messages Table
CREATE TABLE chat_messages (
    message_id SERIAL PRIMARY KEY,
    conversation_id INT NOT NULL,
    user_message TEXT,
    assistant_response TEXT,
    relevant_chunks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
);

CREATE INDEX idx_conv_msg ON chat_messages(conversation_id);
CREATE INDEX idx_user_conv ON conversations(user_id);
CREATE INDEX idx_chunk_embedding ON chunk_embeddings(chunk_id);
CREATE INDEX idx_section_chunk ON document_chunks(section_id);
CREATE INDEX idx_doc_chunk ON document_chunks(doc_id);
CREATE INDEX idx_doc_section ON document_sections(doc_id);
CREATE INDEX idx_user_doc ON documents(user_id);
