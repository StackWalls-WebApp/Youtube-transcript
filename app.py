from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from werkzeug.exceptions import HTTPException
import time
import logging
import random
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Function to load user agents from a file
def load_user_agents(file_path):
    try:
        with open(file_path, 'r') as f:
            user_agents = f.readlines()
        # Strip newlines or any trailing whitespace
        return [ua.strip() for ua in user_agents if ua.strip()]
    except FileNotFoundError:
        logger.error(f"User agents file not found: {file_path}")
        return []

# Function to get a random User-Agent
def get_random_user_agent(user_agents_file):
    user_agents = load_user_agents(user_agents_file)
    if user_agents:
        return random.choice(user_agents)
    else:
        raise ValueError("User agents file is empty or not found")

@app.errorhandler(HTTPException)
def handle_http_exception(e):
    logger.exception(f"HTTP exception occurred: {e}")
    response = e.get_response()
    response.data = jsonify({'error': e.description}).data
    response.content_type = "application/json"
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    logger.exception("An unhandled exception occurred")
    return jsonify({'error': 'An internal server error occurred'}), 500

@app.route('/get_transcript', methods=['POST'])
def get_transcript():
    try:
        video_url = request.json.get('video_url')
        if not video_url:
            logger.error('No video URL provided')
            return jsonify({'error': 'No video URL provided'}), 400

        # Initialize Chrome options for incognito mode and anti-detection measures
        chrome_options = Options()
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')

        # Set random User-Agent from file
        try:
            user_agent = get_random_user_agent('user_agents.txt')
            logger.info(f"Using User-Agent: {user_agent}")
            chrome_options.add_argument(f"user-agent={user_agent}")
        except Exception as e:
            logger.error(f"Error loading user agents: {e}")
            return jsonify({'error': 'Error loading user agents'}), 500

        # Adding extra headers to mimic a legitimate browser request
        chrome_options.add_argument('accept-language=en-US,en;q=0.9')
        chrome_options.add_argument('referer=https://www.google.com')

        # Disable WebDriver detection flags
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Initialize the WebDriver
        try:
            logger.info('Initializing Chrome WebDriver with anti-detection measures')
            driver = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver', options=chrome_options)

            # Overriding navigator.webdriver to avoid detection
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        except Exception as e:
            logger.exception('Error initializing WebDriver')
            return jsonify({'error': 'Error initializing WebDriver'}), 500

        try:
            logger.info('Navigating to NoteGPT YouTube summarizer page')
            driver.get("https://notegpt.io/youtube-video-summarizer")

            # Wait for the input field for the YouTube link to be present
            wait = WebDriverWait(driver, 30)
            logger.info('Waiting for YouTube link input field')
            youtube_link = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[placeholder*='youtube.com']")))

            # Enter the YouTube video link
            logger.info(f'Entering video URL: {video_url}')
            youtube_link.send_keys(video_url)

            # Random wait to simulate human behavior
            time.sleep(random.uniform(2, 5))

            # Wait for the "Generate Summary" button to be clickable
            logger.info('Waiting for "Generate Summary" button')
            generate_button = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.el-button.ng-script-btn.el-button--success")))

            # Simulate human-like behavior with random delays
            time.sleep(random.uniform(1, 3))
            generate_button.click()
            logger.info('Clicked "Generate Summary" button')

            # Wait for the transcript container to appear
            logger.info('Waiting for transcript container')
            transcript_container = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.ng-transcript")))

            # Find the inner scrollable div
            logger.info('Finding inner scrollable div')
            scrollable_div = transcript_container.find_element(By.CSS_SELECTOR, "div[style*='overflow-y: auto']")

            # Initialize a list to store transcript texts in order
            transcript_texts = []

            # Scroll to the top of the scrollable div
            logger.info('Scrolling to the top of the transcript')
            driver.execute_script("arguments[0].scrollTop = 0;", scrollable_div)

            # Wait for initial content to load
            logger.info('Waiting for initial content to load')
            time.sleep(2)

            # Get the total scroll height
            total_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
            viewport_height = driver.execute_script("return arguments[0].clientHeight", scrollable_div)
            logger.info(f'Total scroll height: {total_height}, Viewport height: {viewport_height}')

            # Initialize scroll position
            scroll_position = 0
            scroll_increment = random.randint(6500, 7000)  # Randomize scroll increment
            last_position = -1

            while scroll_position < total_height:
                # Scroll down by random increment
                driver.execute_script("arguments[0].scrollTop = arguments[1];", scrollable_div, scroll_position)
                logger.debug(f'Scrolled to position: {scroll_position}')
                time.sleep(random.uniform(0.5, 1.0))  # Randomize scroll wait time

                # Extract visible transcript items at current scroll position
                transcript_divs = scrollable_div.find_elements(By.CSS_SELECTOR, "div.ng-transcript-item-text")
                logger.debug(f'Found {len(transcript_divs)} transcript items at current position')
                for div in transcript_divs:
                    text = div.text.strip()
                    if text and text not in transcript_texts:
                        transcript_texts.append(text)

                # Update scroll position
                scroll_position += scroll_increment

                # Update total_height in case it changes due to dynamic loading
                new_total_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
                if new_total_height != total_height:
                    logger.info(f'Updated total scroll height: {new_total_height}')
                    total_height = new_total_height

                # Check if we've reached the bottom
                if scroll_position >= total_height or scroll_position == last_position:
                    logger.info('Reached the bottom of the transcript')
                    break

                last_position = scroll_position

            # Ensure all elements are fully loaded
            logger.info('Final wait to ensure all content is loaded')
            time.sleep(random.uniform(2, 5))

            # Combine all transcript texts in order
            full_transcript = "\n".join(transcript_texts)
            logger.info('Transcript extraction completed successfully')

            # Return the transcript as JSON response
            return jsonify({'transcript': full_transcript}), 200

        except TimeoutException:
            logger.error('Transcript container not found. This video might not be accessible.')
            return jsonify({'error': 'This video is not accessible. Please provide another video.'}), 400

        except Exception as e:
            logger.exception('An error occurred during processing')
            return jsonify({'error': 'An internal error occurred during processing'}), 500

        finally:
            logger.info('Closing the WebDriver')
            driver.quit()

    except Exception as e:
        logger.exception('An unexpected error occurred in get_transcript')
        return jsonify({'error': 'An internal server error occurred'}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
