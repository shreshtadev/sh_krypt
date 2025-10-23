# Company and File Metadata API

This is a FastAPI application that provides a RESTful API for managing companies and their file metadata. It allows you to register new companies, manage their API keys, track file metadata, and update usage quotas.

## Features

*   Register new companies and automatically generate API keys.
*   Retrieve company information using an API key.
*   Store and manage file metadata, including file name, size, and key.
*   Track and update company usage quotas.
*   Uses SQLAlchemy for database interactions and Pydantic for data validation.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

*   Python 3.8+
*   A running MariaDB or MySQL database.
*   `uv` (or `pip`) for package management.

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/sh_krypt.git
    cd sh_krypt
    ```

2.  **Create a virtual environment and install dependencies:**

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    uv pip install -r requirements.txt 
    # or if you have pyproject.toml with dependencies
    # uv pip install -e .
    ```

3.  **Configure the database connection:**

    Create a `.env` file in the root directory and add the following environment variables:

    ```
    DATABASE_USER=your_db_user
    DATABASE_PASSWORD=your_db_password
    DATABASE_HOST=localhost
    DATABASE_PORT=3306
    DATABASE_NAME=your_db_name
    IS_DEBUG=True
    ```

### Running the Application

To run the application, use the following command:

```bash
python main.py
```

The application will be available at `http://localhost:9090`.

## API Endpoints

The following are the available API endpoints:

### Company Management

#### `POST /register/company`

Registers a new company.

*   **Request Body:**

    ```json
    {
      "company_name": "string",
      "total_usage_quota": 0,
      "used_quota": 0,
      "aws_bucket_name": "string",
      "aws_bucket_region": "string",
      "aws_access_key": "string",
      "aws_secret_key": "string"
    }
    ```

*   **Response:**

    ```json
    {
      "company_name": "string",
      "start_date": "2025-09-15T15:30:00Z",
      "end_date": "2026-09-15T15:30:00Z",
      "total_usage_quota": 0,
      "used_quota": 0,
      "aws_bucket_name": "string",
      "aws_bucket_region": "string",
      "aws_access_key": "string",
      "aws_secret_key": "string",
      "id": "string",
      "created_at": "2025-09-15T15:30:00Z",
      "company_api_key": "string"
    }
    ```

#### `GET /companies/by-api-key`

Finds a company by its API key.

*   **Headers:**

    *   `company-api-key`: The API key of the company.

*   **Response:**

    Returns the company details as shown in the `POST /register/company` response.

#### `PATCH /companies/quota`

Updates a company's quota.

*   **Headers:**

    *   `company-api-key`: The API key of the company.

*   **Request Body:**

    ```json
    {
      "used_quota": 0,
      "file_txn_type": 1
    }
    ```

*   **Response:**

    Returns the updated company details.

### File Metadata

#### `POST /filemeta`

Inserts new file metadata.

*   **Headers:**

    *   `company-api-key`: The API key of the company.

*   **Request Body:**

    ```json
    {
      "file_name": "string",
      "file_size": 0,
      "file_key": "string",
      "file_txn_type": 1,
      "file_txn_meta": "string"
    }
    ```

*   **Response:**

    ```json
    {
      "file_name": "string",
      "file_size": 0,
      "file_key": "string",
      "file_txn_type": 1,
      "file_txn_meta": "string",
      "id": "string",
      "created_at": "2025-09-15T15:30:00Z"
    }
    ```

## Database Models

The application uses two database models:

*   **`Company`**: Stores information about registered companies, including their API keys, quotas, and AWS details.
*   **`FileMeta`**: Stores metadata about files, including their name, size, and a foreign key relationship to the `Company` model.
