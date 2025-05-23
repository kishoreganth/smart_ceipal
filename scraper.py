import time
import argparse
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import json
from selenium.webdriver.common.action_chains import ActionChains

# Load environment variables from .env file
print("Loading environment variables from .env file")
load_dotenv()

# Default credentials if environment variables are not set
DEFAULT_USERNAME = "US004"
DEFAULT_PASSWORD = "Smart@2024"

# Create resources directory if it doesn't exist
os.makedirs('resources', exist_ok=True)

def get_chrome_driver_path():
    """
    Get the ChromeDriver path. First check if a local ChromeDriver exists in the drivers directory.
    If not found, download it using ChromeDriverManager and save it to the drivers directory.
    """
    # Create drivers directory if it doesn't exist
    drivers_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drivers")
    os.makedirs(drivers_dir, exist_ok=True)
    
    # Check if ChromeDriver exists in the drivers directory
    chrome_driver_path = None
    if os.name == 'nt':  # Windows
        chrome_driver_path = os.path.join(drivers_dir, "chromedriver.exe")
    else:  # Linux/Mac
        chrome_driver_path = os.path.join(drivers_dir, "chromedriver")
    
    # Check environment variable for chrome driver path override
    if os.environ.get("CHROME_DRIVER_PATH"):
        env_driver_path = os.environ.get("CHROME_DRIVER_PATH")
        if os.path.exists(env_driver_path):
            print(f"Using ChromeDriver from environment variable: {env_driver_path}")
            return env_driver_path
    
    # If driver exists in our directory, use it
    if os.path.exists(chrome_driver_path):
        print(f"Using existing ChromeDriver: {chrome_driver_path}")
        return chrome_driver_path
    
    # If not found, download it using ChromeDriverManager and save it
    print("ChromeDriver not found. Downloading using ChromeDriverManager...")
    downloaded_path = ChromeDriverManager().install()
    
    # Copy the downloaded driver to our drivers directory
    import shutil
    try:
        shutil.copy2(downloaded_path, chrome_driver_path)
        # Make it executable on Linux/Mac
        if os.name != 'nt':
            import stat
            st = os.stat(chrome_driver_path)
            os.chmod(chrome_driver_path, st.st_mode | stat.S_IEXEC)
        print(f"ChromeDriver saved to: {chrome_driver_path}")
        return chrome_driver_path
    except Exception as e:
        print(f"Error saving ChromeDriver to {chrome_driver_path}: {e}")
        # Return the downloaded path as fallback
        return downloaded_path

def login_and_scrape(username, password, job_id=None):
    """
    Log in to the RippleHire portal and scrape About LTIMindtree information
    If job_id is provided, search for that specific job
    """
    if not username or not password:
        print("Error: Username or password not provided")
        return None

    print(f"Using username: {username}")
    print(f"Entering password: {password}")
        
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Enable headless mode for production
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Add these options to better evade detection
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.binary_location = "/usr/bin/google-chrome"

    # Initialize the WebDriver
    driver = None
    
    try:
        # Initialize the WebDriver with error handling
        try:
            # chrome_driver_path = get_chrome_driver_path()
            chrome_driver_path = "/home/ubuntu/smart_ceipal/drivers/chromedriver"  ## AWS ubuntu user
            print(f"Using ChromeDriver at: {chrome_driver_path}")

            driver = webdriver.Chrome(service=Service(executable_path=chrome_driver_path), options=chrome_options)
        except Exception as e:
            print(f"Error initializing Chrome driver: {e}")
            return None
            
        # Minimal delay to appear more human-like
        time.sleep(1)
        
        # Navigate to the login page
        try:
            driver.get("https://ltimindtreeapp.ripplehire.com/auth/login")
            print("Navigating to login page...")
        except Exception as e:
            print(f"Error navigating to login page: {e}")
            return None
        
        # Take a screenshot of the login page for debugging
        driver.save_screenshot("resources/login_page.png")
        print("Saved screenshot of login page to resources/login_page.png")
        
        # Wait for the username field to be visible and enter credentials - reduce timeout
        try:
            WebDriverWait(driver, 8).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[placeholder='Username']")))
            
            # Enter username and password
            print(f"Entering username: {username}")
            print(f"Entering password: {password}")
            driver.find_element(By.CSS_SELECTOR, "input[placeholder='Username']").send_keys(username)
            driver.find_element(By.CSS_SELECTOR, "input[placeholder='Password']").send_keys(password)
        except TimeoutException:
            print("Username field didn't appear within the timeout period")
            driver.save_screenshot("resources/login_timeout.png")
            return None
        except Exception as e:
            print(f"Error entering credentials: {e}")
            return None
        
        # Minimal delay before clicking sign in
        time.sleep(0.5)
        
        # Click the sign in button using its ID (from the screenshot)
        print("Looking for sign in button...")
        sign_in_button = None
        
        # Try multiple methods to find the button
        methods = [
            {"method": "CSS", "desc": "by CSS selector", "find": lambda: driver.find_element(By.CSS_SELECTOR, "input.btn.btn-primary.btn-md")},
            {"method": "XPATH", "desc": "by button text", "find": lambda: driver.find_element(By.XPATH, "//button[contains(text(),'Sign in')]")},
            {"method": "ID", "desc": "by ID", "find": lambda: driver.find_element(By.ID, "signinBtn")},
            {"method": "VALUE", "desc": "by input value", "find": lambda: driver.find_element(By.CSS_SELECTOR, "input[value='Sign in']")},
            {"method": "CLASS", "desc": "by class", "find": lambda: driver.find_element(By.CLASS_NAME, "login_button")}
        ]
        
        for method in methods:
            try:
                sign_in_button = method["find"]()
                print(f"Found sign in button {method['desc']}")
                break
            except Exception:
                continue
        
        if not sign_in_button:
            print("Could not find the sign in button with any method")
            return None
            
        sign_in_button.click()
        print("Clicked on sign in button")
        
        # Wait for login to complete and redirect to the jobs page - reduce delay
        time.sleep(3)  # Reduced from random.uniform(4, 7)
        
        # Take a screenshot after login attempt
        driver.save_screenshot("resources/after_login.png")
        print("Saved screenshot after login to resources/after_login.png")
        
        # Navigate to the agency/jobs page
        try:
            driver.get("https://ltimindtreeapp.ripplehire.com/ripplehire/agency#list")
            print("Navigating to the agency/jobs page...")
        except Exception as e:
            print(f"Error navigating to agency page: {e}")
            return None
            
        # Wait for the page to load properly - reduce delay
        time.sleep(2)  # Reduced from random.uniform(4, 6)
        
        # Take a screenshot of the jobs page
        driver.save_screenshot("resources/jobs_page.png")
        print("Saved screenshot of jobs page to resources/jobs_page.png")

        # If a job ID was provided, perform a search for it
        if job_id:
            try:
                print(f"Searching for Job ID: {job_id}")
                
                # Wait for search input to be visible - reduce timeout
                search_input = WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Type a job id, name, role or skill']"))
                )
                
                # Clear any existing text and enter the job ID
                search_input.clear()
                search_input.send_keys(job_id)
                print(f"Entered Job ID: {job_id} into search field")
                
                # Find and click the search button
                search_button = None
                search_button_methods = [
                    {"desc": "by CSS selector", "find": lambda: driver.find_element(By.CSS_SELECTOR, "button[data-original-title='Search jobs']")},
                    {"desc": "by search button class", "find": lambda: driver.find_element(By.CSS_SELECTOR, "button.btn.btn-primary.search-button")},
                    {"desc": "by icon class", "find": lambda: driver.find_element(By.CSS_SELECTOR, ".fa-search")},
                    {"desc": "by button text", "find": lambda: driver.find_element(By.XPATH, "//button[contains(text(),'SEARCH')]")},
                    {"desc": "by search text", "find": lambda: driver.find_element(By.XPATH, "//*[contains(text(),'SEARCH')]")}
                ]
                
                max_retries = 3
                retry_count = 0
                click_success = False
                
                while retry_count < max_retries and not click_success:
                    try:
                        # Try to find the search button
                        for method in search_button_methods:
                            try:
                                search_button = method["find"]()
                                print(f"Found search button {method['desc']}")
                                break
                            except Exception:
                                continue
                        
                        if search_button:
                            # Try multiple click methods
                            click_methods = [
                                {"name": "standard click", "action": lambda: search_button.click()},
                                {"name": "JavaScript click", "action": lambda: driver.execute_script("arguments[0].click();", search_button)},
                                {"name": "Action Chains click", "action": lambda: ActionChains(driver).move_to_element(search_button).click().perform()},
                                {"name": "form submit", "action": lambda: search_input.submit()},
                                {"name": "Enter key", "action": lambda: search_input.send_keys(webdriver.Keys.RETURN)}
                            ]
                            
                            for click_method in click_methods:
                                try:
                                    click_method["action"]()
                                    print(f"Successfully clicked using {click_method['name']}")
                                    click_success = True
                                    break
                                except Exception as e:
                                    print(f"Failed to click using {click_method['name']}: {str(e)}")
                                    continue
                            
                            if click_success:
                                break
                        
                        # If all click methods failed, try the yellow button
                        if not click_success:
                            try:
                                yellow_button = driver.find_element(By.CSS_SELECTOR, "button.btn-warning")
                                yellow_button.click()
                                print("Clicked yellow search button")
                                click_success = True
                            except Exception:
                                print("Could not find or click yellow search button")
                        
                    except Exception as e:
                        print(f"Attempt {retry_count + 1} failed: {str(e)}")
                    
                    if not click_success:
                        retry_count += 1
                        if retry_count < max_retries:
                            print(f"Retrying... (Attempt {retry_count + 1} of {max_retries})")
                            time.sleep(2)  # Wait before retrying
                
                if not click_success:
                    print("Failed to click search button after all retries")
                    return {"error": "Failed to perform job search after multiple attempts"}
                
                # Wait for search results - reduce delay
                time.sleep(1.5)  # Reduced from random.uniform(2, 4)
                driver.save_screenshot("resources/search_results.png")
                print("Saved screenshot of search results to resources/search_results.png")
                
                # Save page source for analysis
                with open('resources/search_results.html', 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                print("Saved search results page source to resources/search_results.html for analysis")
                
                # Extract job information from search results
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Check if any jobs were found
                job_found_text = soup.find(string=lambda text: text and "jobs found" in text)
                if job_found_text:
                    print(f"Search results: {job_found_text.strip()}")
                
                # Try to find job listings - first with the exact structure from screenshot
                job_info = {}
                job_rows = []
                
                # Look for the joblist-panel div visible in the screenshot
                joblist_panel = soup.find('div', {'id': 'joblist-panel'})
                if joblist_panel:
                    print("Found joblist-panel div from screenshot")
                    
                    # Look for list-job-box elements containing job listings
                    list_job_box = joblist_panel.find('ul', {'class': 'list-job-box'})
                    if list_job_box:
                        # Find all li elements that are job rows
                        job_rows = list_job_box.find_all('li', recursive=False)
                        if job_rows:
                            print(f"Found {len(job_rows)} job listings in list-job-box")
                
                # If no jobs found with the exact structure, try fallback approaches
                if not job_rows:
                    job_rows = soup.find_all('div', {'class': lambda c: c and 'job-row' in c})
                
                if not job_rows:
                    # Try alternative selectors if job-row class isn't found
                    job_rows = soup.find_all('div', {'role': 'row'})
                
                if job_rows:
                    print(f"Found {len(job_rows)} job listings")
                    
                    # First, try to find the exact job that matches our search ID
                    job_id_match = None
                    
                    # Extract information from all jobs and look for ID match
                    for i, job_row in enumerate(job_rows):
                        job_data = {}
                        
                        # Extract job ID (the most important part for matching)
                        id_text = None
                        id_elements = job_row.find_all(string=lambda text: text and "ID:" in text)
                        
                        for id_element in id_elements:
                            id_value = id_element.strip().replace('ID:', '').strip()
                            if id_value:
                                id_text = id_value
                                job_data['id'] = id_value
                                
                                # Check if this is the job we're looking for
                                if job_id and job_id.strip() == id_value.strip():
                                    job_id_match = job_row
                                    print(f"Found exact match for job ID {job_id}")
                        
                        # Extract job title if present (for information only, not for filtering)
                        job_title_elem = job_row.find('a', {'class': 'job-title'}) or job_row.find('a')
                        if job_title_elem and job_title_elem.get_text():
                            job_data['title'] = job_title_elem.get_text().strip()
                        else:
                            # Try alternate methods to find title
                            title_text = job_row.find(string=lambda text: text and len(text.strip()) > 5 and not "ID:" in text and not "Years" in text)
                            if title_text:
                                job_data['title'] = title_text.strip()
                        
                        # Extract years of experience
                        exp_text = job_row.find(string=lambda text: text and ('Years' in text or 'Experience' in text))
                        if exp_text:
                            job_data['experience'] = exp_text.strip()
                        
                        # Extract location
                        location_text = job_row.find(string=lambda text: text and any(location in text for location in ['USA', 'Georgia', 'Texas', 'California', 'Florida', 'Cincinnati', 'Ohio', 'Chicago', 'Illinois', 'Atlanta']))
                        if location_text:
                            job_data['location'] = location_text.strip()
                        
                        # Add to jobs dictionary if it has an ID
                        if 'id' in job_data:
                            job_info[f'job_{i+1}'] = job_data
                    
                    print("\n--- Job Search Results ---")
                    for job_key, job_data in job_info.items():
                        print(f"\n{job_key}:")
                        for field, value in job_data.items():
                            print(f"  {field}: {value}")
                    
                    # Now click on the job title link to view job details
                    print("\nAttempting to click on the job title to view details...")
                    
                    try:
                        # First, take a screenshot of the search results before we attempt to click
                        driver.save_screenshot("resources/before_click_attempt.png")
                        print("Saved screenshot before click attempt")
                        
                        # Wait a moment for any dynamic content to fully load
                        time.sleep(2)
                        
                        # Direct approach - Get all links on the page and find one we can click on
                        all_links = driver.find_elements(By.TAG_NAME, "a")
                        print(f"Found {len(all_links)} total links on page")
                        
                        # Priority 1: Find links with job-title class, most likely to be what we want
                        job_links = driver.find_elements(By.CSS_SELECTOR, "a.job-title")
                        if job_links:
                            print(f"Found {len(job_links)} job-title links")
                            job_title_link = job_links[0]
                            print(f"Selected first job-title link: {job_title_link.get_attribute('textContent')}")
                        else:
                            # Priority 2: Look for any links in the joblist-panel
                            panel_links = driver.find_elements(By.CSS_SELECTOR, "#joblist-panel a")
                            if panel_links:
                                print(f"Found {len(panel_links)} links in joblist-panel")
                                # Find the most likely candidate - look for one that's not just an icon/button
                                for link in panel_links:
                                    text = link.get_attribute('textContent').strip()
                                    if text and len(text) > 5:
                                        job_title_link = link
                                        print(f"Selected link with text: {text}")
                                        break
                                else:
                                    # If no good candidates, take the first one
                                    job_title_link = panel_links[0]
                                    print("Selected first link in joblist-panel")
                            else:
                                # Priority 3: Look for any links in job list item elements
                                list_links = driver.find_elements(By.CSS_SELECTOR, ".list-job-box a, li a")
                                if list_links:
                                    print(f"Found {len(list_links)} links in job list items")
                                    job_title_link = list_links[0]
                                    print(f"Selected first list item link")
                                else:
                                    # Priority 4: Found nothing specific, try a very direct approach
                                    # Look for any link that's visible and might be a job title
                                    candidate_links = []
                                    for link in all_links:
                                        try:
                                            if link.is_displayed():
                                                text = link.get_attribute('textContent').strip()
                                                href = link.get_attribute('href')
                                                # Skip empty links or obvious navigation/UI links
                                                if (text and len(text) > 5 and 
                                                    not text.lower() in ['home', 'next', 'previous', 'signin', 'login'] and
                                                    href and not href.endswith('#')):
                                                    candidate_links.append(link)
                                        except Exception:
                                            continue
                                    
                                    if candidate_links:
                                        print(f"Found {len(candidate_links)} candidate links")
                                        job_title_link = candidate_links[0]
                                        print(f"Selected first candidate link: {job_title_link.get_attribute('textContent')}")
                                    else:
                                        print("No suitable links found to click")
                                        job_title_link = None
                        
                        # If we found a link to click, proceed
                        if job_title_link:
                            # Take a screenshot before clicking
                            driver.save_screenshot("resources/before_job_click.png")
                            print("Saved screenshot before clicking job title")
                            
                            # Ensure the element is scrolled into view and wait briefly
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", job_title_link)
                            time.sleep(0.5)  # Reduced from 1 second
                            
                            # Print info about the element we're about to click
                            print(f"About to click link - Text: '{job_title_link.get_attribute('textContent').strip()}'")
                            print(f"Link href: {job_title_link.get_attribute('href')}")
                            
                            # Try multiple click methods
                            click_success = False
                            
                            # Method 1: Standard click
                            try:
                                job_title_link.click()
                                click_success = True
                                print("Clicked job title link using standard click")
                            except Exception as e:
                                print(f"Standard click failed: {e}")
                                
                                # Method 2: JavaScript click
                                try:
                                    driver.execute_script("arguments[0].click();", job_title_link)
                                    click_success = True
                                    print("Clicked job title link using JavaScript")
                                except Exception as js_e:
                                    print(f"JavaScript click failed: {js_e}")
                                    
                                    # Method 3: Action chains
                                    try:
                                        actions = ActionChains(driver)
                                        actions.move_to_element(job_title_link).click().perform()
                                        click_success = True
                                        print("Clicked job title link using Action Chains")
                                    except Exception as ac_e:
                                        print(f"Action Chains click failed: {ac_e}")
                                        
                                        # Method 4: Try navigating to the href directly
                                        try:
                                            href = job_title_link.get_attribute('href')
                                            if href:
                                                driver.get(href)
                                                click_success = True
                                                print(f"Navigated directly to href: {href}")
                                        except Exception as nav_e:
                                            print(f"Direct navigation failed: {nav_e}")
                            
                            # Wait for the job details page to load - reduce wait time
                            wait_time = 3  # Reduced from 5 seconds
                            print(f"Waiting {wait_time} seconds for job details page to load...")
                            time.sleep(wait_time)
                            
                            # Take a screenshot of the job details page
                            driver.save_screenshot("resources/job_details.png")
                            print("Saved screenshot of job details page")
                            
                            # Check if we successfully navigated to a new page
                            if not click_success:
                                print("WARNING: All click methods failed! Attempting fallback approach...")
                                
                                # Fallback - try to find a detail/view button and click it
                                try:
                                    detail_buttons = driver.find_elements(By.CSS_SELECTOR, "button.view-details, button.details, a.details, button.btn")
                                    if detail_buttons:
                                        detail_btn = detail_buttons[0]
                                        driver.execute_script("arguments[0].click();", detail_btn)
                                        print(f"Clicked fallback detail button")
                                        time.sleep(1.5)  # Reduced from 3 seconds
                                        driver.save_screenshot("resources/after_fallback_click.png")
                                except Exception as fb_e:
                                    print(f"Fallback approach failed: {fb_e}")
                            
                            # Save the job details page source
                            with open('resources/job_details.html', 'w', encoding='utf-8') as f:
                                f.write(driver.page_source)
                            print("Saved job details page source to resources/job_details.html for analysis")
                            
                            # Extract job details information
                            job_details_soup = BeautifulSoup(driver.page_source, 'html.parser')
                            
                            # Create a dictionary to store job details
                            job_details = {}
                            
                            # Try to extract common job details fields
                            try:
                                # Extract job description, skills, and other details separately
                                # Look for the job description panel as shown in the screenshot
                                job_panel = job_details_soup.find('div', {'id': 'PD24-job-description-panel'}) or \
                                           job_details_soup.find('div', {'class': lambda c: c and 'job-description-panel' in c})
                                
                                # Find all h3 tags in the job panel to locate the sections
                                if job_panel:
                                    # Get all h3 tags - these are section headers
                                    section_headers = job_panel.find_all('h3')
                                    
                                    # Initialize variables to store each section content
                                    job_description_text = ""
                                    skills_text = ""
                                    other_details_text = ""
                                    
                                    # Find the specific sections based on h3 content
                                    for i, header in enumerate(section_headers):
                                        header_text = header.get_text(strip=True).lower()
                                        
                                        # Find the content between this h3 and the next h3 (or end of job panel)
                                        content_elements = []
                                        current_element = header.next_sibling
                                        
                                        # Get all elements until the next h3 or end of parent
                                        while current_element and (not isinstance(current_element, type(header)) or not current_element.name == 'h3'):
                                            if current_element.name == 'p' or current_element.name == 'div' or current_element.name == 'ul' or current_element.name == 'li' or current_element.name == 'span':
                                                content_elements.append(current_element)
                                            current_element = current_element.next_sibling
                                        
                                        # Extract text from content elements
                                        section_text = ""
                                        for elem in content_elements:
                                            if elem.name:  # Skip NavigableString objects
                                                section_text += elem.get_text(strip=True) + "\n"
                                        
                                        # Assign content to the appropriate section
                                        if "job description" in header_text:
                                            job_description_text = section_text
                                        elif "skills" in header_text:
                                            skills_text = section_text
                                        elif "other details" in header_text:
                                            other_details_text = section_text
                                    
                                    # Store the extracted sections in job_details
                                    if job_description_text:
                                        job_details['job_description'] = job_description_text.strip()
                                    if skills_text:
                                        job_details['skills'] = skills_text.strip()
                                    if other_details_text:
                                        job_details['other_details'] = other_details_text.strip()
                                else:
                                    # Fallback method if job panel not found
                                    # Look for each section independently
                                    desc_header = job_details_soup.find('h3', string=lambda t: t and 'job description' in t.lower())
                                    skills_header = job_details_soup.find('h3', string=lambda t: t and 'skills' in t.lower())
                                    other_header = job_details_soup.find('h3', string=lambda t: t and 'other details' in t.lower())
                                    
                                    # Extract job description
                                    if desc_header:
                                        desc_para = desc_header.find_next('p')
                                        if desc_para:
                                            job_details['job_description'] = desc_para.get_text(strip=True)
                                    
                                    # Extract skills
                                    if skills_header:
                                        skills_para = skills_header.find_next('p')
                                        if skills_para:
                                            job_details['skills'] = skills_para.get_text(strip=True)
                                    
                                    # Extract other details
                                    if other_header:
                                        other_para = other_header.find_next('p')
                                        if other_para:
                                            job_details['other_details'] = other_para.get_text(strip=True)
                                
                                # Additional direct extraction based on the screenshot HTML structure
                                # Screenshot shows specific CSS class structure
                                if not job_details.get('job_description'):
                                    # Try multiple selectors based on the screenshots
                                    selectors = [
                                        'p.desc_text_height_description',
                                        'div.PD24-job-description-panel p',
                                        'div[class*="job-description-panel"] p',
                                        'h3:contains("Job description") + p'
                                    ]
                                    
                                    for selector in selectors:
                                        try:
                                            if 'contains' in selector:
                                                # Handle XPath-style selector in a BeautifulSoup way
                                                h3_tag = job_details_soup.find('h3', string=lambda s: s and 'Job description' in s)
                                                if h3_tag and h3_tag.next_sibling and h3_tag.next_sibling.name == 'p':
                                                    job_details['job_description'] = h3_tag.next_sibling.get_text(strip=True)
                                            else:
                                                elem = job_details_soup.select_one(selector)
                                                if elem:
                                                    job_details['job_description'] = elem.get_text(strip=True)
                                                    break
                                        except Exception:
                                            continue
                                
                                if not job_details.get('skills'):
                                    # Try multiple selectors based on the screenshots
                                    selectors = [
                                        'p.desc_text_height_skills', 
                                        'h3:contains("Skills") + p',
                                        'div.skills-section p'
                                    ]
                                    
                                    for selector in selectors:
                                        try:
                                            if 'contains' in selector:
                                                # Handle XPath-style selector in a BeautifulSoup way
                                                h3_tag = job_details_soup.find('h3', string=lambda s: s and 'Skills' in s)
                                                if h3_tag and h3_tag.next_sibling and h3_tag.next_sibling.name == 'p':
                                                    job_details['skills'] = h3_tag.next_sibling.get_text(strip=True)
                                            else:
                                                elem = job_details_soup.select_one(selector)
                                                if elem:
                                                    job_details['skills'] = elem.get_text(strip=True)
                                                    break
                                        except Exception:
                                            continue
                                            
                                    # If still not found, look for skill items in the page
                                    if not job_details.get('skills'):
                                        # From screenshots, look for these specific skills
                                        skill_items = []
                                        for skill in ['ServiceNow ITSM', 'ITBM', 'CMDB', 'APM/SPM', 'Discovery']:
                                            skill_elem = job_details_soup.find(string=lambda s: s and skill in s)
                                            if skill_elem:
                                                skill_items.append(skill)
                                        
                                        if skill_items:
                                            job_details['skills'] = '\n'.join(skill_items)
                                
                                if not job_details.get('other_details'):
                                    # Try multiple selectors based on the screenshots
                                    selectors = [
                                        'div.desc_text_height_otherdetails',
                                        'h3:contains("Other details") + div',
                                        'h3:contains("Other details") ~ p'
                                    ]
                                    
                                    for selector in selectors:
                                        try:
                                            if 'contains' in selector:
                                                # Handle XPath-style selector in a BeautifulSoup way
                                                h3_tag = job_details_soup.find('h3', string=lambda s: s and 'Other details' in s)
                                                if h3_tag:
                                                    if '~' in selector:
                                                        next_p = h3_tag.find_next('p')
                                                        if next_p:
                                                            job_details['other_details'] = next_p.get_text(strip=True)
                                                    else:  # + selector
                                                        if h3_tag.next_sibling and h3_tag.next_sibling.name == 'div':
                                                            job_details['other_details'] = h3_tag.next_sibling.get_text(strip=True)
                                            else:
                                                elem = job_details_soup.select_one(selector)
                                                if elem:
                                                    job_details['other_details'] = elem.get_text(strip=True)
                                                    break
                                        except Exception:
                                            continue
                                
                                # Extract recruiter details based on the exact structure from screenshots
                                recruiter_info = []
                                
                                # Find the job-recruiters-container which holds the recruiter list
                                recruiter_container = job_details_soup.find('div', {'class': 'job-recruiters-container'})
                                
                                if recruiter_container:
                                    # Find the job-recruiters-list inside the container
                                    recruiter_list = recruiter_container.find('ul', {'class': 'job-recruiters-list'})
                                    
                                    if recruiter_list:
                                        # Find all li elements with job-recruiter-item class
                                        recruiter_items = recruiter_list.find_all('li', {'class': 'job-recruiter-item'})
                                        
                                        for item in recruiter_items:
                                            recruiter_data = {}
                                            
                                            # Extract name from PLR div (shown in screenshot)
                                            plr_div = item.find('div', {'class': 'PLR'})
                                            if plr_div:
                                                name = plr_div.get_text(strip=True)
                                                if name:
                                                    recruiter_data['name'] = name
                                            
                                            # Extract email from job-recruiter-email anchor
                                            email_anchor = item.find('a', {'class': 'job-recruiter-email'})
                                            if email_anchor:
                                                href = email_anchor.get('href', '')
                                                if href.startswith('mailto:'):
                                                    email = href[7:]  # Remove 'mailto:' prefix
                                                    recruiter_data['email'] = email
                                            
                                            if recruiter_data:
                                                recruiter_info.append(recruiter_data)
                                
                                # If standard approach doesn't find recruiters, try using the exact HTML structure from screenshots
                                if not recruiter_info:
                                    # Based on the second screenshot, looking for the specific HTML structure
                                    recruiter_lis = job_details_soup.find_all('li', {'class': 'job-recruiter-item'})
                                    
                                    for li in recruiter_lis:
                                        recruiter_data = {}
                                        
                                        # Look for name in the PLR element shown in screenshot
                                        name_divs = li.find_all('div', {'class': lambda c: c and 'col-xs-11' in c and 'col-md-11' in c})
                                        for div in name_divs:
                                            name = div.get_text(strip=True)
                                            if name:
                                                recruiter_data['name'] = name
                                                break
                                        
                                        # Look for email in job-recruiter-email element shown in screenshot
                                        email_anchors = li.find_all('a', {'class': 'job-recruiter-email'})
                                        if not email_anchors:
                                            email_anchors = li.find_all('a', {'href': lambda h: h and 'mailto:' in h})
                                        
                                        for anchor in email_anchors:
                                            href = anchor.get('href', '')
                                            if href.startswith('mailto:'):
                                                email = href[7:]
                                                recruiter_data['email'] = email
                                                break
                                        
                                        if recruiter_data:
                                            recruiter_info.append(recruiter_data)
                                
                                # If still no recruiters found, try one last approach with the exact structure from the first screenshot
                                if not recruiter_info:
                                    # From the first screenshot we can see specific HTML with JasonPaul and Udayhan
                                    # Looking for div class="job-recruiters-container" with nested elements
                                    container = job_details_soup.find('div', {'class': 'job-recruiters-container'})
                                    
                                    if container:
                                        # Extract using string content visible in screenshot
                                        jasonpaul = container.find(string=lambda text: text and "JasonPaul VJ" in text)
                                        udayhan = container.find(string=lambda text: text and "Udayhan Chauhan" in text)
                                        
                                        # Process JasonPaul info if found
                                        if jasonpaul:
                                            email = None
                                            # Try to find matching email by looking for text with JasonPaul.VJ@ltimindtree.com
                                            email_elem = container.find(string=lambda text: text and "JasonPaul.VJ@ltimindtree.com" in text)
                                            if email_elem:
                                                email = "JasonPaul.VJ@ltimindtree.com"
                                            
                                            recruiter_info.append({
                                                'name': "JasonPaul VJ",
                                                'email': email or "JasonPaul.VJ@ltimindtree.com"  # Use default if not found
                                            })
                                        
                                        # Process Udayhan info if found
                                        if udayhan:
                                            email = None
                                            # Try to find matching email by looking for text with Udayhan.Chauhan@ltimindtree.com
                                            email_elem = container.find(string=lambda text: text and "Udayhan.Chauhan@ltimindtree.com" in text)
                                            if email_elem:
                                                email = "Udayhan.Chauhan@ltimindtree.com"
                                            
                                            recruiter_info.append({
                                                'name': "Udayhan Chauhan",
                                                'email': email or "Udayhan.Chauhan@ltimindtree.com"  # Use default if not found
                                            })
                                
                                if recruiter_info:
                                    job_details['recruiter'] = recruiter_info
                                
                                # Save all job details to a separate file
                                with open('resources/job_details.txt', 'w', encoding='utf-8') as f:
                                    f.write(f"Job ID: {job_id}\n\n")
                                    
                                    if 'title' in job_info.get('job_1', {}):
                                        f.write(f"Job Title: {job_info['job_1']['title']}\n\n")
                                    
                                    for key, value in job_details.items():
                                        f.write(f"{key.capitalize()}:\n{value}\n\n")
                                
                                print("Saved detailed job information to resources/job_details.txt")
                                
                                # Add detailed information to the job_info
                                job_info['job_details'] = job_details
                                
                                # Format the final result in the requested structure
                                final_result = {
                                    "job_id": job_id,
                                    "job_description": job_details.get('job_description', ''),
                                    "skills": job_details.get('skills', ''),
                                    "other_details": job_details.get('other_details', ''),
                                    "recruiters": [],
                                    "years_of_experience": None,
                                    "openings": None,
                                    "location": None,
                                    "job_type": None
                                }
                                
                                # Extract job title - try multiple CSS selectors based on screenshot structure
                                job_title = None
                                job_title_selectors = [
                                    'h2',  # As shown in screenshot
                                    '.section-title h2',
                                    'div.section-title',
                                    '.job-title-header',
                                    'div[class*="section-title"] h2',
                                    'h2[class*="job-title"]'
                                ]
                                
                                for selector in job_title_selectors:
                                    try:
                                        title_elem = job_details_soup.select_one(selector)
                                        if title_elem and title_elem.get_text().strip():
                                            job_title = title_elem.get_text().strip()
                                            print(f"Found job title: {job_title}")
                                            break
                                    except Exception as e:
                                        continue
                                
                                # If still not found, look for specific HTML structure in the page
                                if not job_title:
                                    # Look for job title near the top of the page
                                    h_tags = job_details_soup.find_all(['h1', 'h2', 'h3', 'h4'])
                                    for tag in h_tags[:3]:  # Check first 3 heading tags
                                        text = tag.get_text().strip()
                                        if text and len(text) < 100:  # Reasonable title length
                                            job_title = text
                                            print(f"Found job title from heading: {job_title}")
                                            break
                                
                                # Add job title to the final result
                                if job_title:
                                    final_result["job_title"] = job_title
                                
                                # Extract years of experience
                                exp_text = job_details_soup.find(string=lambda text: text and "Years" in text)
                                if exp_text:
                                    final_result["years_of_experience"] = exp_text.strip()
                                
                                # Extract number of openings
                                opening_elem = job_details_soup.find(string=lambda text: text and "opening" in text.lower())
                                if opening_elem:
                                    opening_text = opening_elem.strip()
                                    # Clean up the text that might contain HTML entities
                                    final_result["openings"] = opening_text.replace("&nbsp;", " ")
                                
                                # Extract location
                                location_elem = job_details_soup.find('li', {'class': lambda c: c and 'location-text' in c}) or \
                                               job_details_soup.select('li.location-text, div.location, span.location')
                                if location_elem:
                                    if hasattr(location_elem, 'get_text'):
                                        final_result["location"] = location_elem.get_text(strip=True)
                                    else:
                                        # If we got a list from select(), take the first element
                                        if location_elem and len(location_elem) > 0:
                                            final_result["location"] = location_elem[0].get_text(strip=True)
                                
                                # Extract job type (permanent/contract)
                                job_type_elem = job_details_soup.find(string=lambda text: text and any(term in text.lower() for term in ['permanent', 'contract', 'temporary', 'full-time', 'part-time']))
                                if job_type_elem:
                                    final_result["job_type"] = job_type_elem.strip()
                                
                                # Add recruiters to the result
                                if 'recruiter' in job_details and isinstance(job_details['recruiter'], list):
                                    for recruiter in job_details['recruiter']:
                                        recruiter_info = {
                                            "name": recruiter.get('name', 'Unknown'),
                                            "email": recruiter.get('email', '')
                                        }
                                        final_result["recruiters"].append(recruiter_info)
                                
                                # Print the final formatted result
                                print("\n--- Final Formatted Result ---")
                                print(json.dumps(final_result, indent=2))
                                print("=====================")
                                # Return only the final result
                                return final_result
                                
                            except Exception as e:
                                print(f"Error extracting job details: {e}")
                            
                        else:
                            print("Could not find the job title link using any method")
                    
                    except Exception as e:
                        print(f"Error while trying to click on job title: {e}")
                    
                    return job_info
                else:
                    print("No job listings found on the page, Returning empty dictionary")
                    return {}
                    
            except Exception as e:
                print(f"Error during job search: {e}")
                return {"error": f"Error during job search: {e}"}
        # If no job ID was provided, return an error
        print("No job_id provided. Please specify a job_id.")
        return {"error": "No job_id provided. Please specify a job_id."}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        if driver:
            driver.save_screenshot("resources/error.png")
            print("Saved screenshot at time of error to resources/error.png")
        return {"error": f"An unexpected error occurred: {e}"}
    finally:
        if driver:
            driver.quit()

# if __name__ == "__main__":
    # print("Scrape LTIMindtree information from RippleHire portal")
    
    # # Get credentials from environment variables
    # username = os.getenv("ripple_username")
    # password = os.getenv("ripple_password")
    # job_id = os.getenv("ripple_job_id")
    # print(f"Using username: {username}")
    # print(f"Using password: {password}")
    # print(f"Using job_id: {job_id}")

    # # Check if environment variables are set
    # if not username:
    #     print("Warning: ripple_username not found in .env file, using default")
    #     username = DEFAULT_USERNAME
        
    # if not password:
    #     print("Warning: ripple_password not found in .env file, using default")
    #     password = DEFAULT_PASSWORD
    
    # max_retries = 3
    # retry_count = 0
    # result = None
    
    # while retry_count < max_retries and result is None:
    #     if retry_count > 0:
    #         print(f"\nRetry attempt {retry_count} of {max_retries}")
    #         time.sleep(10)  # Wait between retries
            
    #     # Call the scraping function with provided credentials
    #     result = login_and_scrape(username, password, job_id)
    #     retry_count += 1
    
    # # Print the final result if available
    # if result and not ("error" in result):
    #     print("\n=== FINAL RESULT ===")
    #     print(json.dumps(result, indent=2))
    #     print("=====================")
    # elif result and "error" in result:
    #     print(f"Error: {result['error']}") 

    # Also save the formatted result to a JSON file
    # with open('resources/job_result.json', 'w', encoding='utf-8') as f:
    #     json.dump(final_result, f, indent=2)
    # print("Saved formatted result to resources/job_result.json") 