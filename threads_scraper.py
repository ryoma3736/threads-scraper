import time
import json
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
import os

class ThreadsScraper:
    def __init__(self):
        # Setup Chrome options
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")  # Run in headless mode (no browser UI)
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Initialize the webdriver
        self.service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=self.service, options=self.chrome_options)
        
    def __del__(self):
        # Clean up the driver when done
        if hasattr(self, 'driver'):
            self.driver.quit()
            
    def get_profile_posts(self, username, max_posts=10):
        """Scrape posts from a Threads profile"""
        profile_url = f"https://www.threads.net/@{username}"
        self.driver.get(profile_url)
        
        # Wait for content to load
        time.sleep(3)
        
        posts = []
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while len(posts) < max_posts:
            # Scroll down to load more content
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Get page source after scrolling
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find all thread posts (adjust the selector based on Threads' HTML structure)
            thread_elements = soup.find_all('div', class_=re.compile('thread-item'))
            
            for element in thread_elements:
                if len(posts) >= max_posts:
                    break
                
                try:
                    # Extract post data (adapt these selectors to match current Threads structure)
                    post_id = element.get('data-thread-id', '')
                    
                    # Find text content
                    text_element = element.find('div', class_=re.compile('thread-content'))
                    text = text_element.get_text(strip=True) if text_element else ''
                    
                    # Find media content (images, videos)
                    media_elements = element.find_all('img', class_=re.compile('media-content'))
                    media_urls = [img.get('src') for img in media_elements if img.get('src')]
                    
                    # Find post date/time
                    time_element = element.find('time')
                    timestamp = time_element.get('datetime') if time_element else ''
                    
                    # Only add unique posts
                    if post_id and post_id not in [p['post_id'] for p in posts]:
                        posts.append({
                            'post_id': post_id,
                            'username': username,
                            'text': text,
                            'media_urls': media_urls,
                            'timestamp': timestamp,
                            'url': f"https://www.threads.net/@{username}/post/{post_id}"
                        })
                except Exception as e:
                    print(f"Error extracting post: {e}")
            
            # Check if we've reached the end of the page
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        return posts
    
    def get_thread_replies(self, thread_url, max_replies=20):
        """Scrape replies for a specific thread"""
        self.driver.get(thread_url)
        
        # Wait for content to load
        time.sleep(3)
        
        replies = []
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while len(replies) < max_replies:
            # Scroll down to load more content
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Get page source after scrolling
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find all reply elements (adjust selector based on Threads' HTML structure)
            reply_elements = soup.find_all('div', class_=re.compile('reply-item'))
            
            for element in reply_elements:
                if len(replies) >= max_replies:
                    break
                
                try:
                    # Extract reply data
                    reply_id = element.get('data-reply-id', '')
                    
                    # Find username
                    user_element = element.find('a', class_=re.compile('user-link'))
                    username = user_element.get_text(strip=True) if user_element else ''
                    
                    # Find text content
                    text_element = element.find('div', class_=re.compile('reply-content'))
                    text = text_element.get_text(strip=True) if text_element else ''
                    
                    # Only add unique replies
                    if reply_id and reply_id not in [r['reply_id'] for r in replies]:
                        replies.append({
                            'reply_id': reply_id,
                            'username': username,
                            'text': text,
                            'thread_url': thread_url
                        })
                except Exception as e:
                    print(f"Error extracting reply: {e}")
            
            # Check if we've reached the end of the page
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        return replies
    
    def download_media(self, posts, download_dir='threads_media'):
        """Download media from posts"""
        import requests
        
        # Create download directory if it doesn't exist
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        
        for post in posts:
            if not post.get('media_urls'):
                continue
                
            post_id = post['post_id']
            post_dir = os.path.join(download_dir, post_id)
            
            if not os.path.exists(post_dir):
                os.makedirs(post_dir)
            
            for i, url in enumerate(post['media_urls']):
                try:
                    response = requests.get(url, stream=True)
                    if response.status_code == 200:
                        # Determine file extension
                        content_type = response.headers.get('content-type', '')
                        if 'image' in content_type:
                            ext = 'jpg' if 'jpeg' in content_type else 'png'
                        elif 'video' in content_type:
                            ext = 'mp4'
                        else:
                            ext = 'bin'  # Default binary file
                        
                        file_path = os.path.join(post_dir, f"{i+1}.{ext}")
                        
                        with open(file_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        print(f"Downloaded: {file_path}")
                    else:
                        print(f"Failed to download media: {url}")
                except Exception as e:
                    print(f"Error downloading media {url}: {e}")
    
    def save_to_csv(self, posts, filename='threads_posts.csv'):
        """Save posts data to CSV"""
        # Convert media_urls list to string for CSV storage
        posts_copy = []
        for post in posts:
            post_copy = post.copy()
            if 'media_urls' in post_copy:
                post_copy['media_urls'] = '|'.join(post_copy['media_urls'])
            posts_copy.append(post_copy)
        
        df = pd.DataFrame(posts_copy)
        df.to_csv(filename, index=False)
        print(f"Saved {len(posts)} posts to {filename}")
    
    def save_to_json(self, posts, filename='threads_posts.json'):
        """Save posts data to JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(posts, f, ensure_ascii=False, indent=4)
        print(f"Saved {len(posts)} posts to {filename}")


# Example usage
if __name__ == "__main__":
    scraper = ThreadsScraper()
    
    # Scrape posts from a profile
    username = "zuck"  # Example: Mark Zuckerberg's Threads account
    posts = scraper.get_profile_posts(username, max_posts=20)
    
    # Save the data
    scraper.save_to_csv(posts)
    scraper.save_to_json(posts)
    
    # Download media from posts
    scraper.download_media(posts)
    
    # Get replies for the first post if any posts were found
    if posts:
        first_post_url = posts[0]['url']
        replies = scraper.get_thread_replies(first_post_url, max_replies=10)
        scraper.save_to_json(replies, 'threads_replies.json')
