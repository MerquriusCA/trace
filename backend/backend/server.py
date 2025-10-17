#!/usr/bin/env python3
"""
Production HTTP server for Chrome extension backend
Deploy to Railway with: railway up
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.request
import ssl
import re
from urllib.parse import urlparse

class CORSHandler(BaseHTTPRequestHandler):
    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/test-get':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            response = {
                'success': True,
                'message': 'GET request successful!',
                'method': 'GET',
                'endpoint': '/api/test-get',
                'timestamp': '2025-01-01T00:00:00Z'
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_error(404, 'Not found')

    def do_POST(self):
        if self.path == '/api/summarize' or self.path == '/api/test':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            # Read request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                request_data = json.loads(post_data.decode('utf-8'))
                print(f"Received request data: {request_data}")
                
                if self.path == '/api/test':
                    # Simple test response
                    response = {
                        'success': True,
                        'message': 'Railway backend is working!',
                        'timestamp': '2025-01-01T00:00:00Z'
                    }
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                
                elif self.path == '/api/summarize':
                    print(f"\n{'='*50}")
                    print(f"📝 SUMMARIZE REQUEST RECEIVED")
                    print(f"{'='*50}")
                    
                    url = request_data.get('url')
                    action = request_data.get('action', 'summarize')
                    api_key = request_data.get('apiKey')
                    
                    print(f"🌐 URL: {url}")
                    print(f"⚙️  Action: {action}")
                    print(f"🔑 API Key present: {bool(api_key)}")
                    print(f"📏 API Key length: {len(api_key) if api_key else 0}")
                    print(f"🕒 Timestamp: {self.date_time_string()}")
                    
                    if not url or not api_key:
                        print(f"❌ ERROR: Missing required data")
                        print(f"   - URL: {'✅' if url else '❌'} {url}")
                        print(f"   - API Key: {'✅' if api_key else '❌'}")
                        self.send_error(400, 'URL and API key required')
                        return
                    
                    # Fetch page content and call OpenAI
                    try:
                        print(f"🔄 Starting content fetch for: {url}")
                        
                        # Fetch the actual page content
                        page_content = self.fetch_page_content(url)
                        if not page_content:
                            print(f"❌ Failed to fetch page content")
                            error_response = {'success': False, 'error': 'Unable to fetch page content'}
                            self.wfile.write(json.dumps(error_response).encode('utf-8'))
                            return
                        
                        print(f"✅ Content fetched successfully ({len(page_content)} chars)")
                        
                        # Call OpenAI API
                        print(f"🤖 Calling OpenAI API for action: {action}")
                        if action == 'analyze':
                            openai_result = self.call_openai_analyze(page_content, api_key)
                        else:
                            openai_result = self.call_openai_summarize(page_content, api_key)
                        
                        if openai_result.get('success'):
                            print(f"✅ OpenAI API call successful")
                            if action == 'summarize':
                                is_article = openai_result.get('is_article', True)
                                print(f"📄 Article detected: {is_article}")
                        else:
                            print(f"❌ OpenAI API call failed: {openai_result.get('error', 'Unknown error')}")
                        
                        self.wfile.write(json.dumps(openai_result).encode('utf-8'))
                        print(f"📤 Response sent successfully")
                        print(f"{'='*50}\n")
                        
                    except Exception as e:
                        print(f"💥 EXCEPTION in summarize endpoint: {str(e)}")
                        print(f"{'='*50}\n")
                        error_response = {'success': False, 'error': str(e)}
                        self.wfile.write(json.dumps(error_response).encode('utf-8'))
                        
            except json.JSONDecodeError:
                self.send_error(400, 'Invalid JSON')
        else:
            self.send_error(404, 'Not found')

    def log_message(self, format, *args):
        print(f"[{self.date_time_string()}] {format % args}")
    
    def fetch_page_content(self, url):
        """Fetch and clean page content from URL"""
        try:
            print(f"Fetching content from: {url}")
            
            # Create request with user agent
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            # Handle SSL context
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(req, context=context, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
            
            # Basic HTML cleaning - remove scripts, styles, and HTML tags
            # Remove script and style elements
            html = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', html, flags=re.IGNORECASE)
            html = re.sub(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', '', html, flags=re.IGNORECASE)
            
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', html)
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Limit content length
            if len(text) > 5000:
                text = text[:5000]
            
            print(f"Extracted {len(text)} characters of text")
            return text
            
        except Exception as e:
            print(f"Error fetching content: {e}")
            return None
    
    def call_openai_summarize(self, content, api_key):
        """Call OpenAI API for summarization"""
        try:
            import json
            
            # First check if this is an article
            article_check_response = self.check_if_article(content, api_key)
            if not article_check_response['is_article']:
                return {
                    'success': True,
                    'summary': article_check_response['message'],
                    'is_article': False
                }
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            
            data = {
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are a helpful assistant that creates concise summaries of web pages. Provide a brief 2-3 sentence summary that captures the main purpose and key information of the page.'
                    },
                    {
                        'role': 'user', 
                        'content': f'Please summarize this web page content in 2-3 sentences:\n\n{content}'
                    }
                ],
                'temperature': 0.3,
                'max_tokens': 150
            }
            
            req = urllib.request.Request(
                'https://api.openai.com/v1/chat/completions',
                data=json.dumps(data).encode('utf-8'),
                headers=headers
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            return {
                'success': True,
                'summary': result['choices'][0]['message']['content'],
                'is_article': True
            }
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return {
                'success': False,
                'error': f'OpenAI API error: {str(e)}'
            }
    
    def call_openai_analyze(self, content, api_key):
        """Call OpenAI API for sentence analysis"""
        try:
            import json
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            
            data = {
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are a helpful assistant that analyzes web page content. When given page text, identify and list the top 5 sentences that best convey the purpose and main message of the page. Format your response as a numbered list with just the sentences, no additional commentary.'
                    },
                    {
                        'role': 'user',
                        'content': f'Here is the page content. Please identify the top 5 sentences that best convey the purpose of this page:\n\n{content}'
                    }
                ],
                'temperature': 0.3,
                'max_tokens': 300
            }
            
            req = urllib.request.Request(
                'https://api.openai.com/v1/chat/completions',
                data=json.dumps(data).encode('utf-8'),
                headers=headers
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            return {
                'success': True,
                'analysis': result['choices'][0]['message']['content']
            }
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return {
                'success': False,
                'error': f'OpenAI API error: {str(e)}'
            }
    
    def check_if_article(self, content, api_key):
        """Check if the page content is a single article vs index/landing page"""
        try:
            import json
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            
            data = {
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {
                        'role': 'system',
                        'content': '''You are an expert at identifying web page types. Analyze the given content and determine if it's a single article/blog post or a homepage/index/listing page.
                        
Article indicators:
- Has a clear title and author
- Contains a coherent narrative or argument
- Focuses on a single topic
- Has substantial body text
- Includes publication date

Non-article indicators:
- Lists of links to other pages
- Multiple unrelated topics
- Navigation menus dominate
- Homepage or landing page
- Category/tag listing page
- Search results page

Respond with JSON: {"is_article": true/false, "confidence": 0-100, "page_type": "article|homepage|listing|navigation|other", "reason": "brief explanation"}'''
                    },
                    {
                        'role': 'user',
                        'content': f'Analyze this page content and determine if it\'s a single article:\n\n{content[:2000]}'
                    }
                ],
                'temperature': 0.1,
                'max_tokens': 150
            }
            
            req = urllib.request.Request(
                'https://api.openai.com/v1/chat/completions',
                data=json.dumps(data).encode('utf-8'),
                headers=headers
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            # Parse the GPT response
            gpt_response = result['choices'][0]['message']['content']
            print(f"Article check response: {gpt_response}")
            
            try:
                analysis = json.loads(gpt_response)
                is_article = analysis.get('is_article', False)
                page_type = analysis.get('page_type', 'unknown')
                confidence = analysis.get('confidence', 0)
                reason = analysis.get('reason', '')
                
                if not is_article:
                    if page_type == 'homepage':
                        message = "This appears to be a homepage or main site page. This tool is designed for summarizing individual articles."
                    elif page_type == 'listing':
                        message = "This appears to be a listing or category page with multiple articles. Please navigate to a specific article to summarize."
                    elif page_type == 'navigation':
                        message = "This appears to be a navigation or menu page. Please select a specific article to summarize."
                    else:
                        message = f"This doesn't appear to be a single article. It looks like a {page_type} page. This tool works best with individual articles or blog posts."
                    
                    return {
                        'is_article': False,
                        'message': message,
                        'confidence': confidence,
                        'page_type': page_type
                    }
                else:
                    return {
                        'is_article': True,
                        'confidence': confidence,
                        'page_type': page_type
                    }
                    
            except json.JSONDecodeError:
                # Fallback if GPT doesn't return valid JSON
                print("Failed to parse GPT response as JSON, using fallback")
                return {
                    'is_article': True,  # Default to true to avoid blocking
                    'confidence': 50,
                    'page_type': 'unknown'
                }
                
        except Exception as e:
            print(f"Error checking article type: {e}")
            # On error, default to allowing summarization
            return {
                'is_article': True,
                'confidence': 0,
                'page_type': 'unknown'
            }

if __name__ == '__main__':
    import os
    
    # Get port from environment variable for cloud deployment
    port = int(os.environ.get('PORT', 8000))
    host = '0.0.0.0'  # Bind to all interfaces for cloud deployment
    
    server = HTTPServer((host, port), CORSHandler)
    print(f"Starting server on {host}:{port}")
    print(f"Test endpoint: http://{host}:{port}/api/test")
    print(f"Summarize endpoint: http://{host}:{port}/api/summarize")
    print("Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()