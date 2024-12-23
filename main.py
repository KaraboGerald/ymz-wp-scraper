from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.permission import Permission
from appwrite.role import Role

import requests
from datetime import datetime, timedelta
from dateutil import parser


def article_exists(databases, database_id, collection_id, article_id):
    """
    Check if article already exists in Appwrite
    """
    try:
        databases.get_document(
            database_id=database_id,
            collection_id=collection_id,
            document_id=f"wp_{article_id}"
        )
        return True
    except Exception:
        return False


def store_article(article, databases, database_id, collection_id, stored_articles):
    """
    Store article in Appwrite database
    """
    try:
        article_id = str(article['id'])
        
        # Skip if already stored in this session
        if article_id in stored_articles:
            print(f"Skipping article {article_id} - already stored in this session")
            return None
            
        # Skip if already exists in Appwrite
        if article_exists(databases, database_id, collection_id, article_id):
            print(f"Skipping article {article_id} - already exists in Appwrite")
            stored_articles.add(article_id)
            return None

        # Format dates to yyyy/mm/dd,HH:MM:SS
        def format_date(date_str):
            date_obj = parser.parse(date_str)
            return date_obj.strftime('%Y/%m/%d,%H:%M:%S')

        # Truncate content if it's too long (49997 chars + "...")
        def truncate_content(content):
            if len(content) > 49997:
                return content[:49997] + "..."
            return content

        # Extract relevant data from WordPress article
        article_data = {
            'wp_id': article_id,
            'title': article['title']['rendered'],
            'content': truncate_content(article['content']['rendered']),
            'excerpt': article['excerpt']['rendered'],
            'slug': article['slug'],
            'link': article['link'],
            'published_date': format_date(article['date']),
            'modified_date': format_date(article['modified']),
            'featured_image': article['_embedded']['wp:featuredmedia'][0]['source_url'] if '_embedded' in article and 'wp:featuredmedia' in article['_embedded'] else None
        }

        # Create document in Appwrite
        result = databases.create_document(
            database_id=database_id,
            collection_id=collection_id,
            document_id=f"wp_{article_id}",
            data=article_data,
            permissions=[
                Permission.read(Role.any())
            ]
        )
        print(f"Successfully stored article {article_id}")
        
        # Add to stored articles set
        stored_articles.add(article_id)
        
        return result
    except Exception as e:
        print(f"Error storing article {article['id']}: {str(e)}")
        return None


def get_articles_by_timeframe(wp_url, timeframe='day'):
    """
    Fetch articles based on timeframe (day, week, month)
    """
    current_time = datetime.utcnow()  # Use UTC time for consistency
    
    if timeframe == 'day':
        start_time = current_time - timedelta(days=1)
    elif timeframe == 'week':
        start_time = current_time - timedelta(weeks=1)
    elif timeframe == 'month':
        start_time = current_time - timedelta(days=30)
    else:
        raise ValueError("Invalid timeframe. Use 'day', 'week', or 'month'")

    # Format the date for WordPress API
    after_date = start_time.isoformat()
    
    # Make the API request
    params = {
        'after': after_date,
        'per_page': 100,  # Maximum posts per request
        '_embed': 1  # Include featured images and other embedded content
    }
    
    wp_api_url = f"{wp_url.rstrip('/')}/wp-json/wp/v2"
    api_url = f"{wp_api_url}/posts"
    print(f"Fetching articles from: {api_url}")
    print(f"Params: {params}")
    
    response = requests.get(api_url, params=params)
    print(f"Response status code: {response.status_code}")
    
    if response.status_code != 200:
        print(f"Error response: {response.text}")
        raise Exception(f"Failed to fetch articles: {response.status_code}")
    
    try:
        articles = response.json()
        print(f"Successfully fetched {len(articles)} articles")
        return articles
    except Exception as e:
        print(f"Error parsing response: {response.text[:500]}")
        raise


def main(context):
    # Initialize Appwrite client
    client = Client()
    client.set_endpoint(context.req.variables.get('APPWRITE_FUNCTION_ENDPOINT', ''))
    client.set_project(context.req.variables.get('APPWRITE_FUNCTION_PROJECT_ID', ''))
    client.set_key(context.req.variables.get('APPWRITE_API_KEY', ''))

    # Get environment variables
    wp_url = context.req.variables.get('WORDPRESS_URL', '')
    database_id = context.req.variables.get('APPWRITE_DATABASE_ID', '')
    collection_id = context.req.variables.get('APPWRITE_COLLECTION_ID', '')

    if not all([wp_url, database_id, collection_id]):
        return context.res.json({
            'success': False,
            'message': 'Missing required environment variables'
        })

    # Initialize services
    databases = Databases(client)
    stored_articles = set()
    total_stored = 0

    # Process articles for different timeframes
    timeframes = ['day', 'week', 'month']
    results = {}

    for timeframe in timeframes:
        try:
            articles = get_articles_by_timeframe(wp_url, timeframe)
            stored_count = 0
            
            for article in articles:
                try:
                    result = store_article(
                        article=article,
                        databases=databases,
                        database_id=database_id,
                        collection_id=collection_id,
                        stored_articles=stored_articles
                    )
                    if result:
                        stored_count += 1
                except Exception as e:
                    print(f"Error processing article {article['id']}: {str(e)}")
                    continue

            results[timeframe] = {
                'fetched': len(articles),
                'stored': stored_count
            }
            total_stored += stored_count

        except Exception as e:
            print(f"Error processing {timeframe} articles: {str(e)}")
            results[timeframe] = {
                'error': str(e)
            }

    return context.res.json({
        'success': True,
        'total_stored': total_stored,
        'results': results
    })
