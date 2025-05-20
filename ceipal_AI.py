import requests
import json
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

# Load environment variables
load_dotenv()

class CeipalAPI:
    """
    Python client for the Ceipal ATS API
    Based on documentation from: https://developer.ceipal.com/ceipal-ats-version-one/authentication
    """
    
    def __init__(self, base_url=None, email=None, password=None, api_key=None):
        """
        Initialize the Ceipal API client
        
        Args:
            base_url: Ceipal API base URL, defaults to env variable CEIPAL_API_URL
            email: Your Ceipal account email, defaults to env variable CEIPAL_EMAIL
            password: Your Ceipal account password, defaults to env variable CEIPAL_PASSWORD
            api_key: Your Ceipal API key, defaults to env variable CEIPAL_API_KEY
        """
        self.base_url = base_url or os.getenv("CEIPAL_API_URL", "https://api.ceipal.com/v1")
        self.auth_url = f"{self.base_url}/createAuthtoken"
        self.jobs_url = f"{self.base_url}/job-postings"
        
        # Auth credentials
        self.email = email or os.getenv("CEIPAL_EMAIL")
        self.password = password or os.getenv("CEIPAL_PASSWORD")
        self.api_key = api_key or os.getenv("CEIPAL_API_KEY")
        
        # Token info
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        
        # Check for required credentials
        if not self.email or not self.password or not self.api_key:
            raise ValueError("CEIPAL_EMAIL, CEIPAL_PASSWORD, and CEIPAL_API_KEY are required. Set them as environment variables or pass them to the constructor.")
    
    def authenticate(self):
        """
        Authenticate with Ceipal API to get access token
        
        Uses email, password and API key for authentication as per Ceipal documentation
        """
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = json.dumps({
            "email": self.email,
            "password": self.password,
            "api_key": self.api_key
        })
        
        response = requests.request("POST", self.auth_url, headers=headers, data=payload)
        
        if response.status_code == 200:
            xml_response = response.text
            print("Authentication response:", xml_response)
            
            try:
                # Parse the XML response
                root = ET.fromstring(xml_response)
                
                # Extract tokens from XML structure
                access_token_elem = root.find("access_token")
                refresh_token_elem = root.find("refresh_token")
                
                if access_token_elem is not None:
                    self.access_token = access_token_elem.text
                else:
                    raise ValueError("No access_token found in the XML response")
                    
                if refresh_token_elem is not None:
                    self.refresh_token = refresh_token_elem.text
                
                # Set expiration time - using a default of 1 hour for access token
                # JWT tokens typically contain expiration info, but we're using a simple approach here
                self.token_expires_at = datetime.now() + timedelta(hours=1)
                
                print("Authentication successful")
                print(f"Access Token: {self.access_token[:20]}...")
                print(f"Refresh Token: {self.refresh_token[:20]}..." if self.refresh_token else "No refresh token received")
                
                return self.access_token
                
            except ET.ParseError as e:
                error_message = f"Error parsing XML response: {str(e)}"
                print(error_message)
                print("Raw response:", xml_response)
                raise Exception(error_message)
                
        else:
            error_message = f"Authentication failed: {response.status_code} - {response.text}"
            print(error_message)
            raise Exception(error_message)
    
    def refresh_auth_token(self):
        """Refresh the authentication token using the refresh token"""
        if not self.refresh_token:
            print("No refresh token available. Performing full authentication instead.")
            return self.authenticate()
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Implement the refresh token endpoint - may need adjustment based on actual API docs
        refresh_url = f"{self.base_url}/refreshToken"  # This endpoint name might need adjustment
        
        payload = json.dumps({
            "refresh_token": self.refresh_token
        })
        
        try:
            response = requests.request("POST", refresh_url, headers=headers, data=payload)
            
            if response.status_code == 200:
                # Parse XML response similar to authenticate method
                xml_response = response.text
                
                try:
                    root = ET.fromstring(xml_response)
                    
                    # Extract tokens from XML structure
                    access_token_elem = root.find("access_token")
                    refresh_token_elem = root.find("refresh_token")
                    
                    if access_token_elem is not None:
                        self.access_token = access_token_elem.text
                    else:
                        print("No access_token in refresh response, falling back to full auth")
                        return self.authenticate()
                        
                    if refresh_token_elem is not None:
                        self.refresh_token = refresh_token_elem.text
                    
                    # Set expiration time
                    self.token_expires_at = datetime.now() + timedelta(hours=1)
                    
                    print("Token refresh successful")
                    return self.access_token
                
                except ET.ParseError as e:
                    error_message = f"Error parsing XML refresh response: {str(e)}"
                    print(error_message)
                    print("Raw response:", xml_response)
                    # Fall back to full authentication
                    return self.authenticate()
            else:
                print(f"Token refresh failed: {response.status_code} - {response.text}")
                # Fall back to full authentication
                return self.authenticate()
        except Exception as e:
            print(f"Token refresh failed: {str(e)}. Performing full authentication instead.")
            return self.authenticate()
    
    def _ensure_authentication(self):
        """Ensure the client has a valid authentication token"""
        if not self.access_token:
            return self.authenticate()
        
        # If token is expired or about to expire in the next minute, refresh it
        if not self.token_expires_at or datetime.now() + timedelta(minutes=1) >= self.token_expires_at:
            try:
                return self.refresh_auth_token()
            except Exception:
                # If refresh fails, try full authentication
                return self.authenticate()
        
        return self.access_token
    
    def get_auth_headers(self):
        """Get headers with authentication token for API requests"""
        token = self._ensure_authentication()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def _xml_to_dict(self, xml_string):
        """Convert XML response to dictionary for easier handling"""
        try:
            root = ET.fromstring(xml_string)
            result = {}
            for child in root:
                result[child.tag] = child.text
            return result
        except ET.ParseError as e:
            print(f"Error parsing XML: {str(e)}")
            return {}
    
    def list_jobs(self, page=1, page_size=20, filters=None):
        """
        List job postings with optional filtering
        
        Args:
            page: Page number for pagination
            page_size: Number of results per page
            filters: Dictionary of filter parameters
        
        Returns:
            List of job postings
        """
        headers = self.get_auth_headers()
        
        params = {
            "page": page,
            "pageSize": page_size
        }
        
        params ={}
        
        # Add any filters
        if filters and isinstance(filters, dict):
            params.update(filters)
        
        list_jobs_url =  "https://api.ceipal.com/v1/getJobPostingsList"
        response = requests.get(list_jobs_url, headers=headers, params=params)
        
        if response.status_code == 200:
            # Check if response is XML or JSON
            content_type = response.headers.get('Content-Type', '')
            if 'xml' in content_type.lower():
                return self._xml_to_dict(response.text)
            else:
                # Try to parse as JSON
                try:
                    return response.json()
                except Exception:
                    # If not JSON, return text
                    return {"text": response.text}
        else:
            error_message = f"Failed to list jobs: {response.status_code} - {response.text}"
            print(error_message)
            raise Exception(error_message)
    
    def get_job(self, job_id):
        """
        Get details for a specific job posting
        
        Args:
            job_id: ID of the job posting
            
        Returns:
            Job posting details
        """
        headers = self.get_auth_headers()
        
        # job_url = f"{self.jobs_url}/{job_id}"
        job_url ="https://api.ceipal.com/v1/getJobPostingDetails/?job_id={job_id}"
        
        response = requests.get(job_url, headers=headers)
        
        if response.status_code == 200:
            # Check if response is XML or JSON
            content_type = response.headers.get('Content-Type', '')
            if 'xml' in content_type.lower():
                return self._xml_to_dict(response.text)
            else:
                # Try to parse as JSON
                try:
                    return response.json()
                except Exception:
                    # If not JSON, return text
                    return {"text": response.text}
        else:
            error_message = f"Failed to get job {job_id}: {response.status_code} - {response.text}"
            print(error_message)
            raise Exception(error_message)
    
    def create_job(self, job_data):
        """
        Create a new job posting
        
        Args:
            job_data: Dictionary containing job posting details
                Required fields may include:
                - title
                - description
                - location
                - jobType
                - businessUnit
                - employmentType
                - salaryFrom
                - salaryTo
                - client
                - hiringManager
                
        Returns:
            Created job posting details
        """
        headers = self.get_auth_headers()
        
        url = "https://api.ceipal.com/savecustomJobPostingDetails/Z3RkUkt2OXZJVld2MjFpOVRSTXoxZz09/5735c56dccb6e492971df18e2cae3b5b/"
        # response = requests.post(self.jobs_url, headers=headers, json=job_data)
        
        response = requests.post(url, headers=headers, json=job_data)
        if response.status_code in [200, 201]:
            print(f"Job posting created successfully")
            # Check if response is XML or JSON
            content_type = response.headers.get('Content-Type', '')
            if 'xml' in content_type.lower():
                return self._xml_to_dict(response.text)
            else:
                # Try to parse as JSON
                try:
                    return response.json()
                except Exception:
                    # If not JSON, return text
                    return {"text": response.text}
        else:
            error_message = f"Failed to create job posting: {response.status_code} - {response.text}"
            print(error_message)
            raise Exception(error_message)
    
    def update_job(self, job_id, job_data):
        """
        Update an existing job posting
        
        Args:
            job_id: ID of the job posting to update
            job_data: Dictionary containing job posting details to update
            
        Returns:
            Updated job posting details
        """
        headers = self.get_auth_headers()
        
        job_url = f"{self.jobs_url}/{job_id}"
        
        response = requests.put(job_url, headers=headers, json=job_data)
        
        if response.status_code == 200:
            print(f"Job posting {job_id} updated successfully")
            # Check if response is XML or JSON
            content_type = response.headers.get('Content-Type', '')
            if 'xml' in content_type.lower():
                return self._xml_to_dict(response.text)
            else:
                # Try to parse as JSON
                try:
                    return response.json()
                except Exception:
                    # If not JSON, return text
                    return {"text": response.text}
        else:
            error_message = f"Failed to update job posting {job_id}: {response.status_code} - {response.text}"
            print(error_message)
            raise Exception(error_message)
    
    def delete_job(self, job_id):
        """
        Delete a job posting
        
        Args:
            job_id: ID of the job posting to delete
            
        Returns:
            True if deletion was successful
        """
        headers = self.get_auth_headers()
        
        job_url = f"{self.jobs_url}/{job_id}"
        
        response = requests.delete(job_url, headers=headers)
        
        if response.status_code == 204:
            print(f"Job posting {job_id} deleted successfully")
            return True
        else:
            error_message = f"Failed to delete job posting {job_id}: {response.status_code} - {response.text}"
            print(error_message)
            raise Exception(error_message)


# Example usage
if __name__ == "__main__":
    # Create API client
    ceipal = CeipalAPI()
    
    try:
        # Authenticate
        access_token = ceipal.authenticate()
        # Print both tokens in a nicely formatted way
        print("\n===== AUTHENTICATION SUCCESSFUL =====")
        print(f"Access Token: {ceipal.access_token[:30]}...{ceipal.access_token[-10:]}")
        print(f"Refresh Token: {ceipal.refresh_token[:30]}...{ceipal.refresh_token[-10:]}")
        print("=====================================\n")
        
        # Create a new job
        # job_data = {
        #     "title": "Senior Python Developer",
        #     "description": "We're looking for a senior Python developer with 5+ years of experience.",
        #     "location": "Remote",
        #     "jobType": "Full-time",
        #     "businessUnit": "Technology",
        #     "employmentType": "Permanent",
        #     "salaryFrom": 100000,
        #     "salaryTo": 130000,
        #     "client": "Internal",
        #     "hiringManager": "John Doe"
        # }
        
        job_payload = [{
            "job_title": "Senior AI Developer",
            "remote_job": 1,
            "job_status": 1,
            "client": "OpenAI",
            "recruitment_manager": "John Doe",
            "job_description": "Work on cutting-edge LLM applications for enterprise clients."
        }]
                
        # Uncomment the following lines to actually create a job
        new_job = ceipal.create_job(job_payload)
        print("new job: ", new_job)
        print(f"Created new job with ID: {new_job.get('id')}")
        
        # List existing jobs
        # jobs = ceipal.list_jobs()
        # print(f"Found {len(jobs.get('data', []))} jobs")
        
    except Exception as e:
        print(f"Error: {str(e)}")
