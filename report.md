# Report of daily weather & news @Budapest ETL pipeline

## 1. Adding Custom Dependencies

To integrate the `openmeteo_requests` package for the weather API, follow these steps:

### Step 1: Define `requirements.txt`

Create a `requirements.txt` file to list all necessary dependencies, including `openmeteo_requests`.

### Step 2: Modify the Docker Setup

1. Create a new `Dockerfile` in the same directory based on the `apache/airflow` image to install the required dependencies.
2. Update the `docker-compose` configuration:
   - Uncomment the `build: .` line.
   - Comment out the `image: ${AIRFLOW_IMAGE_NAME:-apache/airflow:2.10.5}` line.
3. **Note:** Do not build the new `Dockerfile` separately.

### Step 3: Build and Deploy

Run the following commands to build and start the Airflow environment with the updated dependencies:

```bash
docker compose up --build airflow-init
docker compose up

```

## 2. Implementation details
