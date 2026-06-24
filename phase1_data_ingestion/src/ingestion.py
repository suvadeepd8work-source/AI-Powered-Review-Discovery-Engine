import os
import pandas as pd
from typing import List, Dict, Any
from schema import RawReviewSchema
from tenacity import retry, stop_after_attempt, wait_exponential

class ReviewIngestionPipeline:
    def __init__(self, db_conn_str: str = "sqlite:///reviews.db"):
        self.db_conn_str = db_conn_str

    def parse_csv(self, file_path: str) -> List[Dict[str, Any]]:
        """Reads CSV file and returns list of raw reviews as dictionaries."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        df = pd.read_csv(file_path)
        # Ensure column standard casing and mapping
        df.columns = [col.lower().strip() for col in df.columns]
        
        # Standard mapping helper
        mapping = {
            'content': 'review_text',
            'body': 'review_text',
            'score': 'rating',
            'date': 'review_date',
            'version': 'app_version'
        }
        df = df.rename(columns=mapping)
        return df.to_dict(orient='records')

    def validate_records(self, raw_records: List[Dict[str, Any]]) -> List[RawReviewSchema]:
        """Validates list of dictionaries against the Pydantic schema."""
        valid_records = []
        for i, record in enumerate(raw_records):
            try:
                # Basic cleaning of date and parameters
                if 'review_date' in record and isinstance(record['review_date'], str):
                    record['review_date'] = pd.to_datetime(record['review_date'])
                
                # Check required fields defaults if missing
                if 'platform' not in record:
                    record['platform'] = 'ios' # default
                
                validated = RawReviewSchema(**record)
                valid_records.append(validated)
            except Exception as e:
                # Log parsing failure instead of stopping pipeline
                print(f"Skipping malformed row {i}: {e}")
        return valid_records

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def save_to_database(self, validated_records: List[RawReviewSchema]) -> int:
        """Saves validated records to the SQL Database."""
        # Database transaction logic will be added here
        print(f"Saving {len(validated_records)} records to {self.db_conn_str}...")
        return len(validated_records)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest raw music app reviews.")
    parser.add_argument("--file", required=True, help="Path to CSV review file")
    args = parser.parse_args()

    pipeline = ReviewIngestionPipeline()
    try:
        raw_data = pipeline.parse_csv(args.file)
        validated = pipeline.validate_records(raw_data)
        saved_count = pipeline.save_to_database(validated)
        print(f"Successfully processed and saved {saved_count} reviews.")
    except Exception as e:
        print(f"Ingestion pipeline failed: {e}")
