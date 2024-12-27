
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/get_transcript', methods=['POST'])
def get_transcript():
    video_url = request.json.get('video_url')
    if not video_url:
        logger.error('No video URL provided')
        return jsonify({'error': 'No video URL provided'}), 400

    # Initialize Chrome options for incognito mode
    chrome_options = Options()
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')

    # Initialize the WebDriver
    try:
        logger.info('Initializing Chrome WebDriver')
        driver = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver', options=chrome_options)
    except Exception as e:
        logger.exception('Error initializing WebDriver')
        return jsonify({'error': 'Error initializing WebDriver'}), 500

    try:
        logger.info('Navigating to NoteGPT YouTube summarizer page')
        driver.get("https://notegpt.io/youtube-video-summarizer")

        # Wait until the input field for the YouTube link is present
        wait = WebDriverWait(driver, 30)
        logger.info('Waiting for YouTube link input field')
        youtube_link = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "input[placeholder*='youtube.com']")))

        # Enter the YouTube video link
        logger.info(f'Entering video URL: {video_url}')
        youtube_link.send_keys(video_url)

        # Wait for the "Generate Summary" button to be clickable
        logger.info('Waiting for "Generate Summary" button')
        generate_button = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button.el-button.ng-script-btn.el-button--success")))
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
        scroll_increment = 500  # Adjust as needed
        last_position = -1

        while scroll_position < total_height:
            # Scroll down by increment
            driver.execute_script("arguments[0].scrollTop = arguments[1];", scrollable_div, scroll_position)
            logger.debug(f'Scrolled to position: {scroll_position}')
            time.sleep(0.1)  # Adjust as needed

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
        time.sleep(2)

        # Combine all transcript texts in order
        full_transcript = "\n".join(transcript_texts)
        logger.info('Transcript extraction completed successfully')

        # Return the transcript as JSON response
        return jsonify({'transcript': full_transcript}), 200

    except Exception as e:
        logger.exception('An error occurred during processing')
        return jsonify({'error': str(e)}), 500
    finally:
        logger.info('Closing the WebDriver')
        driver.quit()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')


'''
##To initialize to run in cmd
chromedriver_path = '/usr/local/bin/chromedriver'  # Update path as needed
service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)
'''