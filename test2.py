from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

app = Flask(__name__)

# Set up Chrome WebDriver
chrome_driver_path = "/usr/local/bin/chromedriver"  # Adjust the path to your chromedriver
service = Service(chrome_driver_path)
options = Options()

# Add headless mode for running without a GUI
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument("window-size=1920x1080")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36")

# Define a route to scrape jobs
@app.route('/scrape_jobs', methods=['POST'])
def scrape_jobs():
    input_data = request.json
    job_title = input_data.get('job', 'Data Scientist')  # Default to 'Data Scientist' if not provided
    location = input_data.get('location', 'Mumbai')  # Default to 'Mumbai' if not provided
    experience = input_data.get('experience', '5')  # Default to '5' years if not provided

    driver = webdriver.Chrome(service=service, options=options)

    try:
        # Construct the URL based on inputs
        url = f"https://www.naukri.com/{job_title.replace(' ', '-')}-jobs-in-{location}?experience={experience}"
        driver.get(url)

        # Wait explicitly for the job listings to appear
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.srp-jobtuple-wrapper'))
        )

        # Find all job listings
        jobs = driver.find_elements(By.CSS_SELECTOR, 'div.srp-jobtuple-wrapper')

        # List to hold all job data
        job_data_list = []

        for job in jobs:
            try:
                # Extract basic details from the job card
                job_title = job.find_element(By.CSS_SELECTOR, 'a.title').text
                company_name = job.find_element(By.CSS_SELECTOR, 'a.comp-name').text
                rating_element = job.find_elements(By.CSS_SELECTOR, 'a.rating')
                ratings = rating_element[0].text if rating_element else "No rating"
                experience = job.find_element(By.CSS_SELECTOR, 'span.expwdth').text
                salary = job.find_element(By.CSS_SELECTOR, 'span.sal').text
                location = job.find_element(By.CSS_SELECTOR, 'span.locWdth').text
                job_description_summary = job.find_element(By.CSS_SELECTOR, 'span.job-desc').text
                skills_elements = job.find_elements(By.CSS_SELECTOR, 'ul.tags-gt li')
                skills = [skill.text for skill in skills_elements]
                posting_date = job.find_element(By.CSS_SELECTOR, 'span.job-post-day').text
                job_link = job.find_element(By.CSS_SELECTOR, 'a.title').get_attribute('href')

                # Open the job detailed page to get more info
                driver.execute_script("window.open(arguments[0], '_blank');", job_link)
                driver.switch_to.window(driver.window_handles[1])
                time.sleep(3)  # Wait for the detailed job page to load

                # Extract additional details
                role = industry_type = department = employment_type = role_category = education_ug = education_pg = key_skills = ""

                try:
                    sections = driver.find_elements(By.CSS_SELECTOR, 'div.styles_details_Y424')
                    for section in sections:
                        try:
                            label = section.find_element(By.CSS_SELECTOR, 'label').text.strip()
                            value = section.find_element(By.CSS_SELECTOR, 'span').text.strip()

                            if "Role" in label:
                                role = value
                            elif "Industry Type" in label:
                                industry_type = value
                            elif "Department" in label:
                                department = value
                            elif "Employment Type" in label:
                                employment_type = value
                            elif "Role Category" in label:
                                role_category = value
                            elif "UG" in label:
                                education_ug = value
                            elif "PG" in label:
                                education_pg = value
                        except:
                            continue

                except Exception as e:
                    print(f"Error extracting additional details: {e}")

                # Extract detailed job description
                try:
                    job_desc_section = driver.find_element(By.CSS_SELECTOR, 'div.styles_JDC__dang-inner-html__h0K4t').text
                except:
                    job_desc_section = "Not available"

                # Extract key skills
                try:
                    key_skills_elements = driver.find_elements(By.CSS_SELECTOR, 'div.styles_key-skill_GIPn_ a')
                    key_skills = ', '.join([skill.text for skill in key_skills_elements])
                except:
                    key_skills = ""

                # Create job dictionary with all details
                job_data = {
                    "Job Title": job_title,
                    "Company Name": company_name,
                    "Ratings": ratings,
                    "Experience": experience,
                    "Salary": salary,
                    "Location": location,
                    "Job Description (Summary)": job_description_summary,
                    "Skills": skills,
                    "Posting Date": posting_date,
                    "Job Link": job_link,
                    "Job Details": {
                        "Job Description": job_desc_section,
                        "Role": role,
                        "Industry Type": industry_type,
                        "Department": department,
                        "Employment Type": employment_type,
                        "Role Category": role_category,
                        "Education": {
                            "UG": education_ug,
                            "PG": education_pg
                        },
                        "Key Skills": key_skills
                    }
                }

                # Add the job data to the list
                job_data_list.append(job_data)

                # Close the detailed job tab and switch back to the listing tab
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(2)

            except Exception as e:
                print(f"Error extracting data for a job: {e}")

        return jsonify(job_data_list)

    except Exception as e:
        return jsonify({"error": str(e)})
    
    finally:
        driver.quit()

if __name__ == "__main__":
    app.run(debug=True)
