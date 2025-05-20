# Ceipal API Client

This Python client provides a convenient way to interact with the Ceipal ATS API for managing job postings, applicants, and more.

## Setup

1. Install the required packages:
   ```
   pip install requests python-dotenv
   ```

2. Create a `.env` file in your project directory with your Ceipal API credentials:
   ```
   CEIPAL_API_URL=https://api.ceipal.com/v1
   CEIPAL_EMAIL=your_email_here
   CEIPAL_PASSWORD=your_password_here
   CEIPAL_API_KEY=your_api_key_here
   ```

   You can copy the `.env-sample` file and rename it to `.env` to get started.

3. Import the `CeipalAPI` class in your Python code:
   ```python
   from ceipal_AI import CeipalAPI
   ```

## Authentication

This client uses the official Ceipal authentication method which requires your email, password, and API key.
As per Ceipal documentation: "CEIPAL API uses a combination of Username, Password, and API Key to authenticate and generate a Bearer Token."

Keep your API credentials secure and consider rotating your API password regularly.

## Usage Examples

### Authentication

```python
from ceipal_AI import CeipalAPI

# Initialize the API client
ceipal = CeipalAPI()

# Authenticate (required before any API operations)
ceipal.authenticate()
```

### Creating a Job Posting

```python
# First authenticate
ceipal.authenticate()

# Prepare job data
job_data = {
    "title": "Senior Python Developer",
    "description": "We're looking for a senior Python developer with 5+ years of experience.",
    "location": "Remote",
    "jobType": "Full-time",
    "businessUnit": "Technology",
    "employmentType": "Permanent",
    "salaryFrom": 100000,
    "salaryTo": 130000,
    "client": "Internal",
    "hiringManager": "John Doe"
}

# Create the job posting
new_job = ceipal.create_job(job_data)
print(f"Created new job with ID: {new_job.get('id')}")
```

### Listing Job Postings

```python
# Get the first page of job postings with default page size (20)
jobs = ceipal.list_jobs()

# Get specific page with custom page size
jobs = ceipal.list_jobs(page=2, page_size=50)

# With filters
filters = {
    "status": "Active",
    "jobType": "Full-time"
}
jobs = ceipal.list_jobs(filters=filters)

print(f"Found {len(jobs.get('data', []))} jobs")
```

### Getting Job Details

```python
# Get details for a specific job
job_id = "12345"
job_details = ceipal.get_job(job_id)
print(f"Job title: {job_details.get('title')}")
```

### Updating a Job Posting

```python
job_id = "12345"
update_data = {
    "title": "Updated Job Title",
    "salaryTo": 150000
}
updated_job = ceipal.update_job(job_id, update_data)
```

### Deleting a Job Posting

```python
job_id = "12345"
success = ceipal.delete_job(job_id)
```

## Error Handling

The client includes robust error handling. All methods will raise an Exception with details if an API call fails:

```python
try:
    ceipal.authenticate()
    new_job = ceipal.create_job(job_data)
except Exception as e:
    print(f"Error: {str(e)}")
```

## Extending the Client

This client currently focuses on job posting operations. You can extend it to handle other Ceipal API endpoints like:

- Applicants
- Submissions
- Talent Bench
- Clients
- Leads
- Vendors
- Interviews
- Placements

For more information, refer to the [official Ceipal API documentation](https://developer.ceipal.com/ceipal-ats-version-one/authentication). 