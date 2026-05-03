# Incident Hub - Mission-Critical Incident Management System

**Deployed Frontend:** [https://incident-hub-eta.vercel.app/](https://incident-hub-eta.vercel.app/)

Incident Hub is a high-performance, resilient incident management platform designed for Site Reliability Engineering (SRE) teams. It is built to handle extreme signal volumes, providing automated ingestion, intelligent debouncing, and structured lifecycle management for critical system failures.

## 1. Overview

In modern distributed systems, a single failure often triggers a "storm" of thousands of redundant signals. Incident Hub solves this by decoupling ingestion from processing. It ingests high-volume telemetry (up to 10,000 signals/sec), offloads them to a distributed queue, and uses an asynchronous worker to debounce duplicates and create manageable Work Items.

Key focus areas:
- **Resilience**: Protects the source of truth from ingestion spikes.
- **Noise Reduction**: Automated debouncing based on component health windows.
- **Accountability**: Strict state transitions and mandatory Root Cause Analysis (RCA).

## 2. Architecture Overview

The system follows a distributed, asynchronous architecture to ensure zero-loss ingestion and low-latency monitoring.

### ASCII Architecture Diagram
```text
[ External Sensors ] --(HTTP POST)--> [ Ingestion API ]
                                            |
                                            +--> [ MongoDB (Raw Signals) ]
                                            |
                                            +--> [ Redis Stream / Queue ]
                                                       |
                                             [ Signal Processor Worker ]
                                                       |
                                            +----------+----------+
                                            |                     |
                                    [ PostgreSQL (SOT) ]    [ Redis Cache ]
                                            |                     |
[ SRE Dashboard ] <----(HTTP GET)---- [ Dashboard API ] <---------+
```

### Data Flow
1. **Ingestion**: The API receives a signal, persists the raw payload to MongoDB for auditability, and enqueues a processing task in Redis.
2. **Processing**: The Worker service consumes the signal, checks for active debouncing windows in Redis, and either updates an existing Work Item or creates a new one in PostgreSQL.
3. **Observability**: As Work Items are updated, the Worker seeds the Redis Cache to ensure the Dashboard can serve data with zero database overhead.
4. **Lifecycle**: SREs interact with the API to transition incidents through states (OPEN, INVESTIGATING, RESOLVED, CLOSED).

## 3. Key Features
- **High-Throughput Ingestion**: Non-blocking API capable of handling 10,000+ signals per second.
- **Asynchronous Processing**: Decoupled worker architecture ensures API responsiveness regardless of DB load.
- **Intelligent Debouncing**: Grouping of related signals within a configurable time window to reduce alert fatigue.
- **State Machine Enforcement**: Strict sequential transitions (OPEN → CLOSED) using the State Pattern.
- **Mandatory RCA**: Critical safety guard preventing incident closure without a valid Root Cause Analysis.
- **Automated MTTR**: Native calculation of Mean Time To Resolve based on lifecycle timestamps.
- **Performance Cache**: Redis Hash-based dashboard for sub-millisecond read latency.
- **Backpressure Handling**: Redis-backed rate limiting and queue-based buffering to protect downstream services.

## 4. Project Structure
```text
/backend
  /app
    /api        # FastAPI routes and middleware (CORS, Rate Limiting)
    /core       # Global configuration, logging setup, and security
    /models     # Pydantic schemas and persistence models
    /services   # Client wrappers for PostgreSQL, MongoDB, and Redis
    /workers    # Asynchronous signal processors and background tasks
    /utils      # Helper functions for MTTR and state logic
/frontend       # React (Vite) application with Tailwind CSS 4
/docker-compose.yml
/README.md
```

## 5. Setup Instructions

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)
- Node.js 20+ (for local frontend development)

### Deployment
```bash
# Clone the repository
git clone https://github.com/RealCifer/Incident-Hub.git
cd Incident-Hub

# Build and start all services
docker-compose up --build -d
```

### Services and Ports
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **MongoDB**: localhost:27017
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## 6. API Overview
- `POST /signals`: Ingests raw telemetry data. Returns 202 Accepted.
- `GET /dashboard`: Returns a cached snapshot of all active incidents.
- `GET /workitems/{id}`: Retrieves detailed state and history for a specific incident.
- `POST /rca/{id}`: Submits a Root Cause Analysis (Required for closure).
- `PATCH /workitems/{id}/transition`: Executes a state machine transition.
- `GET /health`: Returns connectivity status for all downstream dependencies.

## 7. Backpressure Handling Strategy
To handle bursts of 10,000+ signals, the system implements a **Queue-Worker** pattern.
- **Decoupling**: The Ingestion API does not write to the transactional database (PostgreSQL). It only writes to a fast NoSQL store (MongoDB) and a queue (Redis).
- **Buffering**: Redis acts as a buffer. If PostgreSQL or the Worker service slows down, signals accumulate safely in the queue rather than crashing the API or dropping data.
- **Load Shedding**: A Redis-backed rate limiter protects the ingestion endpoint from being overwhelmed beyond capacity.

## 8. Debouncing Strategy
To prevent "alert storms," the system uses a **Sliding Window Debouncer**:
- When a signal arrives, the Worker checks Redis for an active `debounce:{component_id}` key.
- If present, the signal is linked to the existing Work Item without triggering new notifications.
- The window (default 10s) effectively groups rapid-fire failures into a single actionable incident.

## 9. Workflow Engine Design
The system implements a formal State Machine:
- **States**: `OPEN` → `INVESTIGATING` → `RESOLVED` → `CLOSED`.
- **Transitions**: Controlled via the State Pattern, ensuring only valid forward movements.
- **RCA Guard**: The transition to `CLOSED` is programmatically blocked unless an RCA document (containing category, fix, and prevention steps) is present.

## 10. Observability
- **Structured Logging**: All logs are emitted in JSON format for easy ingestion by ELK/Splunk.
- **Health Checks**: `/health` endpoint provides deep checks into DB and Redis connectivity.
- **Lifecycle Auditing**: Every state transition and signal link is logged with timestamps and component metadata.

## 11. Reliability Considerations
- **Exponential Backoff**: All database interactions are wrapped in retry logic to handle transient network failures.
- **Optimistic Concurrency**: Atomic MongoDB/PostgreSQL updates prevent race conditions during state transitions.
- **Fail-Safe Dashboard**: If the Redis cache is purged, the system automatically triggers a cold-start rebuild from the source of truth.

## 12. Sample Data / Testing
A seeding script is provided to simulate a production environment.
```bash
python scripts/seed_data.py
```
Alternatively, use `curl` to manually trigger an incident:
```bash
curl -X POST http://localhost:8000/signals \
     -H "Content-Type: application/json" \
     -d '{"component_id": "payment-gateway", "payload": {"error": "timeout"}}'
```

## 13. Design Decisions and Tradeoffs
- **Redis vs. Direct DB**: Redis is used for ingestion to ensure the API response time is independent of database latency (Consistency vs. Availability).
- **Dual DB Strategy**: MongoDB is used for raw, schemaless signals (high write volume), while PostgreSQL is used for structured, transactional incident data (data integrity).
- **Eventual Consistency**: The dashboard is eventually consistent with the source of truth to prioritize read performance.
