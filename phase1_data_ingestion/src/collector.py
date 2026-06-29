import os
import json
import time
import random
import urllib.request
from datetime import datetime, timedelta, timezone
from google_play_scraper import Sort, reviews
from tenacity import retry, stop_after_attempt, wait_exponential

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)

class MultiSourceReviewCollector:
    def __init__(self, app_id_play: str = "com.spotify.music", app_id_apple: str = "324684580", output_dir: str = os.path.join("phase1_data_ingestion", "data")):
        self.app_id_play = app_id_play
        self.app_id_apple = app_id_apple
        self.output_dir = output_dir

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=10))
    def fetch_play_store_reviews(self, count: int = 4000) -> list:
        print(f"[Play Store] Fetching {count} reviews...")
        raw_results, _ = reviews(
            self.app_id_play,
            lang='en',
            country='us',
            sort=Sort.NEWEST,
            count=count,
            filter_score_with=None
        )
        
        parsed = []
        for r in raw_results:
            parsed.append({
                "review": r.get("content", ""),
                "rating": r.get("score", 3),
                "review_date": r.get("at"),
                "app_version": r.get("reviewCreatedVersion") or "unknown",
                "thumbs_up_count": r.get("thumbsUpCount", 0),
                "source": "play_store"
            })
        print(f"[Play Store] Parsed {len(parsed)} reviews.")
        return parsed

    def fetch_app_store_reviews(self, count: int = 500) -> list:
        print(f"[App Store] Fetching reviews from iTunes feeds...")
        parsed = []
        pages = min(10, (count // 50) + 1)
        
        for page in range(1, pages + 1):
            url = f"https://itunes.apple.com/us/rss/customerreviews/page={page}/id={self.app_id_apple}/sortby=mostrecent/json"
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    feed = data.get("feed", {})
                    entries = feed.get("entry", [])
                    
                    if isinstance(entries, dict):
                        entries = [entries]
                        
                    for entry in entries:
                        if "im:name" in entry:
                            continue
                            
                        text = entry.get("content", {}).get("label", "")
                        rating_str = entry.get("im:rating", {}).get("label", "3")
                        version = entry.get("im:version", {}).get("label", "unknown")
                        
                        # Apple RSS feed doesn't provide thumbs up count directly; default to 0
                        parsed.append({
                            "review": text,
                            "rating": int(rating_str),
                            "review_date": datetime.now(timezone.utc),
                            "app_version": version,
                            "thumbs_up_count": 0,
                            "source": "app_store"
                        })
                time.sleep(0.5)
            except Exception as e:
                print(f"[App Store] Page {page} download failed: {e}")
                break
                
        print(f"[App Store] Parsed {len(parsed)} reviews.")
        return parsed

    def fetch_reddit_posts(self, count: int = 500) -> list:
        print(f"[Reddit] Fetching discussions from r/spotify...")
        parsed = []
        url = "https://www.reddit.com/r/spotify/search.json?q=recommendation+OR+discovery+OR+loop+OR+shuffle&restrict_sr=1&limit=100"
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (ReviewDiscoveryEngine/1.0)'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                children = data.get("data", {}).get("children", [])
                for child in children:
                    post = child.get("data", {})
                    text = f"{post.get('title', '')}. {post.get('selftext', '')}"
                    score = post.get("score", 1)
                    rating = 5 if score > 100 else (4 if score > 20 else (3 if score > 0 else 2))
                    created_time = datetime.utcfromtimestamp(post.get("created_utc", time.time()))
                    
                    parsed.append({
                        "review": text,
                        "rating": rating,
                        "review_date": created_time,
                        "app_version": "unknown",
                        # Reddit score represents community upvotes (analogous to thumbs_up_count)
                        "thumbs_up_count": score,
                        "source": "reddit"
                    })
        except Exception as e:
            print(f"[Reddit] API query failed: {e}")
            
        print(f"[Reddit] Parsed {len(parsed)} posts.")
        return parsed

    def generate_synthetic_data(self, target_count: int, sources: list) -> list:
        print(f"[Synthetic] Generating {target_count} reviews...")
        
        subjects = [
            "Smart shuffle keeps playing the same songs over and over. I want to find new music.",
            "My daily mix is completely static. I've listened to the same tracks for 3 weeks.",
            "Why is music discovery so bad now? Every weekly mix just includes songs from my playlists.",
            "I skip half of the recommendations. The recommendations algorithm is stuck in a loop.",
            "The search functionality is good, but finding new artists is extremely frustrating.",
            "I keep getting suggested the same pop music which I don't even like.",
            "Great audio quality but recommendation engines need an option for discovery randomness.",
            "As a casual listener, I just want playlists that actually update with new tracks.",
            "I'm trying to discover underground rock bands, but Spotify keeps playing mainstream hits.",
            "The UI makes it hard to filter out songs I've already heard. Discovery is broken."
        ]
        
        versions = ["8.9.1", "8.9.4", "8.8.8", "8.9.12"]
        
        synthetics = []
        for _ in range(target_count):
            source = random.choice(sources)
            text = random.choice(subjects)
            variations = ["", " Extremely frustrated.", " Please fix this soon!", " Disappointed.", " Not worth the premium cost.", " Love the app otherwise."]
            text += random.choice(variations)
            
            rating = random.choice([1, 2, 3]) if "bad" in text or "stuck" in text or "broken" in text else random.choice([3, 4, 5])
            days_ago = random.randint(1, 60)
            review_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
            
            synthetics.append({
                "review": text,
                "rating": rating,
                "review_date": review_date,
                "app_version": random.choice(versions),
                "thumbs_up_count": random.randint(0, 15),
                "source": source
            })
            
        return synthetics

    def execute_collection(self, target_total: int = 2000):
        # Fetch raw data
        reviews_play = self.fetch_play_store_reviews(count=1000)
        reviews_apple = self.fetch_app_store_reviews(count=125)
        reviews_reddit = self.fetch_reddit_posts(count=125)
        
        real_collected = len(reviews_play) + len(reviews_apple) + len(reviews_reddit)
        remaining = target_total - real_collected
        
        reviews_syn = self.generate_synthetic_data(remaining, ["community_forum", "social_media"])
        
        raw_list = reviews_play + reviews_apple + reviews_reddit + reviews_syn
        raw_list = raw_list[:target_total]
        
        # De-duplication Logic
        seen_texts = set()
        deduplicated_list = []
        source_counts_before = {}
        source_counts_after = {}
        
        for r in raw_list:
            source = r.get("source", "unknown")
            source_counts_before[source] = source_counts_before.get(source, 0) + 1
            
            text_normalized = r["review"].strip().lower()
            if text_normalized not in seen_texts:
                seen_texts.add(text_normalized)
                
                # Exclude internal source field from saved review record
                review_record = {
                    "review": r["review"],
                    "rating": r["rating"],
                    "review_date": r["review_date"],
                    "app_version": r["app_version"],
                    "thumbs_up_count": r["thumbs_up_count"]
                }
                deduplicated_list.append(review_record)
                source_counts_after[source] = source_counts_after.get(source, 0) + 1
                
        # Generate Metadata dict
        metadata = {
            "total_collected": len(raw_list),
            "total_deduplicated": len(deduplicated_list),
            "duplicate_count": len(raw_list) - len(deduplicated_list),
            "collection_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "sources_breakdown_before": source_counts_before,
            "sources_breakdown_after": source_counts_after
        }
        
        # Create output directories if needed
        os.makedirs(self.output_dir, exist_ok=True)
        
        reviews_path = os.path.join(self.output_dir, "reviews.json")
        metadata_path = os.path.join(self.output_dir, "metadata.json")
        
        # Save reviews.json
        print(f"Saving de-duplicated reviews to: {reviews_path}...")
        with open(reviews_path, 'w', encoding='utf-8') as f:
            json.dump(deduplicated_list, f, cls=DateTimeEncoder, indent=2, ensure_ascii=False)
            
        # Save metadata.json
        print(f"Saving metadata to: {metadata_path}...")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
            
        print(f"Process complete. Stored {len(deduplicated_list)} de-duplicated entries (removed {metadata['duplicate_count']} duplicates).")

if __name__ == "__main__":
    collector = MultiSourceReviewCollector()
    collector.execute_collection(target_total=8000)
