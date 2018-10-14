PRAGMA foreign_keys = ON;

CREATE TABLE flow (
id VARCHAR(36) PRIMARY KEY,
content BLOB
);

CREATE TABLE body (
id INTEGER PRIMARY KEY,
flow_id VARCHAR(36),
type_id INTEGER,
content BLOB,
FOREIGN KEY(flow_id) REFERENCES flow(id)
);

CREATE TABLE annotation (
id INTEGER PRIMARY KEY,
flow_id VARCHAR(36),
type VARCHAR(16),
content BLOB,
FOREIGN KEY(flow_id) REFERENCES flow(id)
);
