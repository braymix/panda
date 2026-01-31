sql
CREATE TABLE events (
    id UUID PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    city VARCHAR(120) NOT NULL,
    venue VARCHAR(200),
    category VARCHAR(80) NOT NULL,
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ,
    organizer VARCHAR(160),
    price NUMERIC(10,2),
    url VARCHAR(400),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_start_at ON events (start_at);
CREATE INDEX idx_city ON events (city);
CREATE INDEX idx_category ON events (category);
CREATE INDEX idx_title ON events USING BTREE (title);