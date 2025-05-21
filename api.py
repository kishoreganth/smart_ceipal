from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import os
from scraper import login_and_scrape
from dotenv import load_dotenv
import time
from ceipal_AI import CeipalAPI
import aiohttp
import json
from openai import AsyncOpenAI

# Load environment variables
load_dotenv()

# Define Pydantic models for request validation
class PromptRequest(BaseModel):
    prompt: str
    # max_tokens: int = 500
    temperature: float = 0.7

# Initialize OpenAI client
async_openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI(
    title="LTIMindtree Job Scraper API",
    description="API to retrieve job details from LTIMindtree RippleHire portal",
    version="1.0.0"
)

@app.get("/job/details")
async def get_job_details(job_id: str = Query(..., description="The job ID to search for"),
                           country: str = Query(None, description="The country to search in (USA or INDIA)")):
    """
    Get job details from LTIMindtree RippleHire portal
    
    Returns job description and recruiter information for the specified job ID
    """
    try:
        # Validate country parameter
        if not country:
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "Country parameter is required. Please specify either 'USA' or 'INDIA'.",
                    "data": []
                },
                status_code=200
            )
            
        # Convert country to uppercase for case-insensitive comparison
        country = country.upper()
        if country not in ["USA", "INDIA"]:
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "Invalid country. Please specify either 'USA' or 'INDIA'.",
                    "data": []
                },
                status_code=200
            )

        if country == "USA":
            # Get credentials from environment variables
            username = os.getenv("ripple_username")
            password = os.getenv("ripple_password")
        else:
            username = os.getenv("ripple_username_india")
            password = os.getenv("ripple_password_india")
        
        if not username or not password:
            raise HTTPException(
                status_code=500, 
                detail="Missing credentials. Please set ripple_username and ripple_password environment variables."
            )
        
        # Call the scraping function with the provided job ID
        print(f"Attempting to scrape job details from ripplehire for job ID: {job_id}")
        result = login_and_scrape(username, password, job_id)
                
        print("result ", result)
        print("type of result ", type(result))
        print(f"Scraper returned result: {result is not None}")
        
        # check if result is empty or job description is empty
        if not result or not result.get("job_description"):
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "No job details found or job description is empty. Please check the job ID.",
                    "data": []
                },
                status_code=200
            )

        # # # Transform the result into the required data format
        data = transform_job_data(result)
        print("transformed data ", data)
        
        

        
        # Format and clean the job description and extract job title and rate information
        if data and data[0].get("job_description"):
            print("Formatting job description...")
            formatted_jd = await gen_ai_output(data[0]["job_description"])
            print("Job description formatted successfully")
            print("\n")
            print("AI output ", formatted_jd)
            print("\n")
            
            # Update the job description with the formatted version
            data[0]["job_description"] = formatted_jd["job_description"]
            data[0]["client_bill_rate___salary"] = formatted_jd["rate"] if formatted_jd["rate"] else "N/A"
            # data[0]["client_bill_rate___salary"] = 24
            # data[0]["description_cleaned"] = True
            
            # check if the job title is a contractor job and a variable for both condition like a flag to pass in gen_ai_output
            # IF contractor job then job_title should be extracted from the job description using gen_ai_output( formatted_jd )
            if "contractor" in data[0]["job_title"].lower():
                data[0]["job_type"] = 7
                data[0]["job_title"] = formatted_jd["job_title"]
            else:
                data[0]["job_type"] = 1
            
        else:
            print("No job description to format")
            # data[0]["description_cleaned"] = False
        # data[0]["job_title"] = data[0]["job_title"][:50]
        # Create job post in Ceipal
        final_data = {}
        final_data["recruitment_manager"] = data[0]["recruitment_manager"]
        final_data["job_title"] = data[0]["job_title"]
        
        try:
            ceipal = CeipalAPI(country)
            ceipal_data =[{
                "job_title": data[0]["job_title"],
                "remote_job": 1,
                "job_status": 6,
                # "country": "",
                "client": "z5G7h3l6a1kMvyS65NP3c1Wey4ZBSspA_4KksTSjJxU=",
                # "states": 0,
                "recruitment_manager":"z5G7h3l6a1kMvyS65NP3c0wyhFsf0_8F-nELY1aw5Wk=",
                # "city": "",
                "job_type": data[0]["job_type"],
                "client_manager": data[0]["client_manager"],
                "client_job_id": data[0]["client_job_id"],
                "primary_skills": data[0]["primary_skills"],
                "location": data[0]["location"],
                "job_description": data[0]["job_description"],
                "client_bill_rate___salary": data[0]["client_bill_rate___salary"]
            }]
            print("DATA ", data)
            # This is to create the job post in Ceipal and get the job URL
            new_data = create_job_post(data, ceipal, country)
            print("new data ", new_data)
            print("type of new data ", type(new_data))
            
            if new_data is None:
                return JSONResponse(
                    content={
                        "status": "error",
                        "message": "Failed to create Ceipal job post",
                        "data": []
                    },
                    status_code=200
                )
                
            dummy_created_job = [{'status': 201, 'job_code': 'JPC -  31435', 'job_posting_id': 31429, 'message': 'Job posting created successfully.', 'success': 'Y'}]
            # job_details = ceipal.get_job("31429")
            all_jobs_listing_details = ceipal.list_jobs()
            all_job_results = all_jobs_listing_details.get('results', [])
            print("job details ", all_job_results[0])
            if all_job_results[0]["job_code"] == new_data[0]["job_code"]: 
                
                final_data["ceipal_job_id"] = all_job_results[0]["id"]
                final_data["apply_job_without_registration"] = all_job_results[0]["apply_job_without_registration"]
                final_data["job_description"] = data[0]["job_description"]
                final_data["status"] = "Job Posted Successfully"
                print("final data ", final_data)
                return final_data
                # return all_job_results[0]["apply_job_without_registration"]
            
        except Exception as e:
            print(f"Warning: Failed to create job post in Ceipal: {str(e)}")
            final_data["status"] = "Job Posted Failed"
            return final_data
            # Continue since this is not a critical failure
        
        # return data
        # return 1
        
    except Exception as e:
        print(f"Error in get_job_details: {str(e)}")
        # Return a default response instead of failing completely
        data = transform_job_data(None)  # Generate default data
        return JSONResponse(
            content={
                "status": "error",
                "message": f"An error occurred: {str(e)}",
                "data": data
            },
            status_code=500
        )

# async def search_contacts_by_name(
#     name: str = Query(..., description="Name to search for"),
#     api_key: str = Query(None, description="API key for Ceipal. If not provided, uses environment variable")
# ):
#     """
#     Search for client contacts by name
    
#     Returns a list of client contacts that match the specified name
#     """
#     try:
#         # Get all contacts
#         all_ceipal_client_manager = await get_client_contacts(api_key)
        
#         if not all_ceipal_client_manager:
#             return JSONResponse(
#                 content={
#                     "status": "warning",
#                     "message": "No client contacts found",
#                     "data": []
#                 },
#                 status_code=200
#             )
        
#         # Search for matching contacts

#         matches = find_contact_by_name(all_ceipal_client_manager, name)
        
#         # Return the results
#         return JSONResponse(
#             content={
#                 "status": "success",
#                 "message": f"Found {len(matches)} matching contacts",
#                 "search_term": name,
#                 "data": matches
#             },
#             status_code=200
#         )
    
#     except Exception as e:
#         return JSONResponse(
#             content={
#                 "status": "error",
#                 "message": f"An error occurred: {str(e)}",
#                 "data": []
#             },
#             status_code=500
#         )

def transform_job_data(result):
    """
    Transform the job scraping result into the required data format
    """
    # Check if result is None
    if result is None:
        print("WARNING: result is None, creating an empty data object")
        # Return an empty data object with default values
        return [{
            "job_title": "Unknown Position",
            "remote_job": 1,
            "job_status": 6,
            # "country": "",
            "client": "z5G7h3l6a1kMvyS65NP3c1Wey4ZBSspA_4KksTSjJxU=",
            # "states": 0,
            "recruitment_manager":"z5G7h3l6a1kMvyS65NP3c0wyhFsf0_8F-nELY1aw5Wk=",
            # "city": "",
            "job_description": "",
            "job_type": 0,
            "client_manager": "",
            "client_job_id": "",
            "primary_skills": "",
            "location": ""
        }]
    
    # Parse location into component parts
    location = result.get('location', '') or ''  # Ensure we get a string even if None
    location_parts = location.split(' - ')
    city = state = country = ''
    
    if len(location_parts) >= 3:
        city = location_parts[0]
        state = location_parts[1]
        country = location_parts[2]
    elif len(location_parts) == 2:
        city = location_parts[0]
        state = location_parts[1]
    elif len(location_parts) == 1 and location_parts[0]:
        city = location_parts[0]
    
    # Transform job type
    job_type_value = result.get('job_type', '') or ''
    # This will configure the job type as permanent or contract
    job_type = 1 if job_type_value.lower() == "permanent" else 7
    
    # Transform recruiters to recruitment_manager (taking the first one if multiple exist)
    recruitment_manager = ""
    recruiters = result.get('recruiters') or []
    if recruiters and len(recruiters) > 0:
        recruiter = recruiters[0]
        if isinstance(recruiter, dict):
            # Format as "Name <Email>" if both are available
            if recruiter.get('name') and recruiter.get('email'):
                recruitment_manager = f"{recruiter['name']} <{recruiter['email']}>"
            # Just name if only name is available
            elif recruiter.get('name'):
                recruitment_manager = recruiter['name']
            # Just email if only email is available
            elif recruiter.get('email'):
                recruitment_manager = recruiter['email']
        else:
            # If it's not a dict, convert whatever it is to string
            recruitment_manager = str(recruiter)
    
    # Extract job title - first check if it's already in the result
    job_title = result.get('job_title', '') or ''
    job_description = result.get('job_description', '') or ''
    client_job_id = result.get('job_id', '') or ''
    primary_skills = result.get('skills', '') or ''
    openings = result.get('openings', '') or ''
    
    # Build the transformed data object
    data = [{
        "job_title": job_title,
        "remote_job": 1,
        "job_status": 1 if openings else 0,
        # "country": country,
        # "country": 0,
        "client": "z5G7h3l6a1kMvyS65NP3c1Wey4ZBSspA_4KksTSjJxU=",
        # "states": state,
        # "states":0,
        "recruitment_manager": "z5G7h3l6a1kMvyS65NP3c0wyhFsf0_8F-nELY1aw5Wk=",
        # "city": city,
        # "city": 0,
        "job_description": job_description,
        "job_type": job_type,
        "client_job_id": client_job_id,
        "primary_skills": primary_skills,
        "location": location,
        "client_manager": recruitment_manager  # This will be the ripple recruiter
    }]
    
    return data


def create_job_post(data, ceipal, country):
    
    try:
        access_token = ceipal.authenticate()
        access_token = ceipal.authenticate()

        print("Authenticated with Ceipal API, sending job data...")
        # Use the country-specific URL from the CeipalAPI instance
        new_job = ceipal.create_job(data, country)
        print("API Response:", new_job)
        # print(f"Created new job with ID: {new_job.get('id')}")
        return new_job
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

# async def get_client_contacts(api_key=None):
#     """
#     Get client contacts from the Ceipal API
    
#     Args:
#         api_key (str, optional): API key for authentication. If None, uses environment variable.
        
#     Returns:
#         list: List of client contacts with their details
#     """
#     try:
#         # Use provided API key or get from environment variables
#         if api_key is None:
#             api_key = os.getenv("CEIPAL_API_KEY")
#             if not api_key:
#                 raise ValueError("No API key provided and CEIPAL_API_KEY environment variable not set")
        
#         # Create the URL with the API key
#         url = f"https://api.ceipal.com/{api_key}/getClientContacts/"
        
#         # Use aiohttp for async HTTP requests
#         async with aiohttp.ClientSession() as session:
#             async with session.get(url) as response:
#                 if response.status != 200:
#                     raise Exception(f"API request failed with status code {response.status}: {await response.text()}")
                
#                 # Parse the JSON response
#                 data = await response.json()
#                 print("data ", data)
#                 return data
      
#     except Exception as e:
#         print(f"Error in get_client_contacts: {str(e)}")
#         return []


# def find_contact_by_name(all_client_manager, name):
#     """
#     Find contacts by name using a for loop with if condition
    
#     Args:
#         contacts (list): List of contact dictionaries
#         name (str): Name to search for (case insensitive)
        
#     Returns:
#         list: List of matching contacts
#     """
#     matching_contacts = []
    
#     # Convert search name to lowercase for case-insensitive comparison
#     search_name = name.lower().strip()
    
#     # Loop through each contact
#     for contact in all_client_manager:
#         # Check if contact_first_name exists in the contact
#         if "contact_first_name" in contact:
#             # Get the name and convert to lowercase for comparison
#             contact_name = contact["contact_first_name"].lower().strip()
            
#             # Check if the contact name matches the search name
#             if contact_name in search_name:
#                 matching_contacts.append(contact)
                
#     return matching_contacts


# Example usage:
# result = {
#     "job_id": "707965",
#     "job_description": "Job Title: ServiceNow ITOM Architect...",
#     "skills": "Mandatory Skills :ServiceNow ITOM...",
#     "other_details": "Benefits/perks listed below...",
#     "recruiters": [
#         {
#             "name": "Uthayakumar Nagarajan",
#             "email": "Uthayakumar.Nagarajan@ltimindtree.com"
#         }
#     ],
#     "years_of_experience": "10-16 Years",
#     "openings": "1 Opening",
#     "location": "Covington - Kentucky - USA",
#     "job_type": "Permanent"
# }
# 
# data = transform_job_data(result)
# print(data)


async def gen_ai_output(prompt, temperature=0.7):
    """
    Generate AI output using OpenAI's GPT-3.5 Turbo model
    
    Args:
        prompt (str): The prompt to send to the AI model
        is_contractor_job (bool): Flag to check if the job is a contractor job
        temperature (float): Sampling temperature
    
    Returns:
        dict: JSON object containing formatted job description, extracted rate information, and job title
    """
    try:
        # Strong system prompt for processing job descriptions
        system_prompt = """
            You are a professional job description formatter with expertise in cleaning and enhancing job postings. 
            Your task is to:

            1. IMPORTANT: Extract ANY mention of hourly rates, costs, compensation amounts, or payment information. This includes:
            - Dollar amounts (e.g., $50/hr, $65,000/year)
            - Hourly rates in any currency
            - Salary ranges or specific figures
            - Contract rates or budgets
            - Any other financial compensation details

            2. Extract the job title from the description:
            - Look for "Job Title:", "Position:", "Role:", or similar indicators
            - If no specific indicator is found, determine the most likely job title from the context
            - The extracted title should reflect the specific role (e.g., "Senior Java Developer" rather than just "Contractor")

            3. Format the job description to be more professional and readable:
            - Use proper paragraphing and spacing
            - Organize content into clear sections (Responsibilities, Requirements, etc.)
            - Correct any grammatical or spelling errors
            - Maintain all original technical details and job requirements
            - Keep all skills, qualifications, and company information intact

            4. CRITICAL: DO NOT add ANY new information that wasn't in the original job description:
            - DO NOT create new requirements or qualifications
            - DO NOT add skills that weren't specified
            - DO NOT invent company information or benefits
            - DO NOT expand on responsibilities or duties
            - DO NOT add your own interpretation or additional context
            - DO NOT create new sections that weren't implied in the original

            5. Return a JSON object with three keys:
            - "job_description": The reformatted job description with rate information removed
            - "rate": All extracted rate information. If no rate information is found, return an empty string
            - "job_title": The extracted job title from the description. Be specific and detailed.

            6. IMPORTANT: Return ONLY the raw JSON object without any markdown code block markers or additional text. 
            - Do NOT wrap your response in ```json or ``` markers
            - The response should start with { and end with }
            - No explanations or other text before or after the JSON

            Your job is to:
            1. Extract and separately return any rate information
            2. Extract and separately return the specific job title
            3. Format the text for readability
            4. Correct grammar/spelling
            5. NEVER add new information
            6. Return the result as a valid JSON object with the specified structure

            Process the job description I will share with you and return the cleaned, improved version as raw JSON.
            """

        # Call the OpenAI API with the provided prompt and enhanced system prompt
        response = await async_openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here is the job description to format and extract job title and any rate information:\n\n{prompt}"}
            ],
            max_tokens= 10000,
            temperature=temperature
        )
        
        # Extract the generated text from the response
        if response and response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content.strip()
            
            # Clean the content by removing markdown code block markers
            if content.startswith("```json"):
                content = content[7:]  # Remove ```json prefix
            elif content.startswith("```"):
                content = content[3:]  # Remove ``` prefix
            
            if content.endswith("```"):
                content = content[:-3]  # Remove ``` suffix
            
            content = content.strip()
            
            try:
                # Parse the JSON response
                result = json.loads(content)
                return result
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}. Content: {content}")
                # If parsing fails, return a structured error response
                return {
                    "job_description": content,
                    "rate": "",
                    "job_title": ""
                }
        else:
            return {
                "job_description": "Sorry, I couldn't generate a response.",
                "rate": "",
                "job_title": ""
            }
    
    except Exception as e:
        print(f"Error in gen_ai_output: {str(e)}")
        return {
            "job_description": f"Error generating AI response: {str(e)}",
            "rate": "",
            "job_title": ""
        }

@app.get("/")
async def home():
    return {"message": "Welcome to the LTIMindtree Job Scraper API"}

if __name__ == "__main__":
    # Start the API server when script is run directly
    uvicorn.run(app, host="0.0.0.0", port=5000) 
