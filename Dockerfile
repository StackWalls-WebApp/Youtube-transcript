# Use an official Python runtime as a parent image
FROM python:3.12-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    gnupg \
    curl \
    jq \
    libnss3 \
    libxss1 \
    libappindicator1 \
    fonts-liberation \
    xdg-utils \
    libu2f-udev \
    libgbm-dev \
    libasound2 \
    libnspr4 \
    libx11-xcb1 \
    libxtst6 \
    lsb-release \
    libgbm1 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list' && \
    apt-get update && \
    apt-get install -y google-chrome-stable

# Download ChromeDriver from the provided link
RUN wget -O /tmp/chromedriver-linux64.zip https://storage.googleapis.com/chrome-for-testing-public/129.0.6668.70/linux64/chromedriver-linux64.zip

# Unzip and move to the correct location
RUN unzip /tmp/chromedriver-linux64.zip -d /usr/local/bin/ && rm /tmp/chromedriver-linux64.zip

# Make ChromeDriver executable
RUN chmod +x /usr/local/bin/chromedriver-linux64/chromedriver

# Create symlink for ChromeDriver
RUN ln -s /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the user_agents.txt file
COPY user_agents.txt /app/

# Copy the application code
COPY . .

# Expose port 5000 for Flask
EXPOSE 5000

# Run app.py when the container launches using gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
