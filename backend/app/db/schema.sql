CREATE TABLE IF NOT EXISTS intersections (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    zone VARCHAR(100) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    lane_count INTEGER NOT NULL,
    road_width DOUBLE PRECISION NOT NULL,
    road_priority_weight DOUBLE PRECISION NOT NULL DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS traffic_snapshots (
    id SERIAL PRIMARY KEY,
    intersection_id INTEGER NOT NULL REFERENCES intersections(id),
    captured_at TIMESTAMP NOT NULL DEFAULT NOW(),
    vehicle_count INTEGER NOT NULL,
    vehicle_type_distribution JSONB NOT NULL,
    traffic_density_score DOUBLE PRECISION NOT NULL,
    emergency_detected BOOLEAN NOT NULL DEFAULT FALSE,
    occupancy_index FLOAT DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS signal_plans (
    id SERIAL PRIMARY KEY,
    intersection_id INTEGER NOT NULL REFERENCES intersections(id),
    generated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    green_time_seconds INTEGER NOT NULL,
    density_score DOUBLE PRECISION NOT NULL,
    priority_score DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS emergency_routes (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    severity_level INTEGER NOT NULL,
    source VARCHAR(150) NOT NULL,
    route_intersections JSONB NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);
