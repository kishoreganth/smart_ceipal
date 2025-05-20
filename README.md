# LTIMindtree Job Scraper API

This API allows you to scrape job details from the LTIMindtree RippleHire portal using a FastAPI application.

## Setup

1. Clone this repository
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root with the following credentials:
   ```
   ripple_username=YOUR_USERNAME
   ripple_password=YOUR_PASSWORD
   ```

## Running the API

Run the API server with:

```
python api.py
```

The server will start on port 5000. You can access the API documentation at:
- http://localhost:5000/docs
- http://localhost:5000/redoc

## API Endpoints

### GET /job/details/

Fetches job details from the LTIMindtree portal.

**Query Parameters:**
- `job_id` (required): The job ID to search for

**Example Response:**
```json
{
  "job_id": "12345",
  "job_description": "Designing and Planning Implementations in ITOM and SPM Modules to achieve Business Outcomes\nSkills: Extensive Practical Exposure on ITOM and SPM Module Designing and Implementation",
  "mandatory_skills": ["ServiceNow ITOM", "ServiceNow ITSM", "ITBM", "CMDB", "APM/SPM", "Discovery"],
  "other_details": "Benefits/perks listed below may vary depending on the nature of your employment with LTIMindtree (\"LTIM\"):\nBenefits and Perks:\n- Comprehensive Medical Plan Covering Medical, Dental, Vision\n- Short Term and Long-Term Disability Coverage\n- 401(k) Plan with Company match",
  "recruiters": [
    {
      "name": "Recruiter Name",
      "email": "recruiter.name@ltimindtree.com"
    }
  ],
  "years_of_experience": "10-16 Years",
  "openings": "1 Opening",
  "location": "Covington - Kentucky - USA",
  "job_type": "Permanent"
}
```

## Running the Scraper Directly

If you want to run the scraper without the API:

```
python scraper.py
```

Set the following environment variable in your `.env` file to specify a job ID:
```
ripple_job_id=YOUR_JOB_ID
```

## Notes

- The scraper uses Selenium with Chrome WebDriver
- Make sure Chrome is installed on your system
- Screenshots and HTML files are saved during the scraping process for debugging purposes 