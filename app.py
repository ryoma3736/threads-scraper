from flask import Flask, jsonify, request
from threads_scraper import ThreadsScraper
import logging
import time

app = Flask(__name__)

# セットアップログ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/api/profile_posts', methods=['GET'])
def get_profile_posts():
    username = request.args.get('username')
    max_posts = int(request.args.get('max_posts', 10))
    
    if not username:
        return jsonify({"error": "Username is required"}), 400
    
    try:
        logger.info(f"Scraping posts for @{username}")
        scraper = ThreadsScraper()
        posts = scraper.get_profile_posts(username, max_posts=max_posts)
        
        # スクレイパークリーンアップ
        del scraper
        
        return jsonify({
            "username": username,
            "post_count": len(posts),
            "posts": posts
        })
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
