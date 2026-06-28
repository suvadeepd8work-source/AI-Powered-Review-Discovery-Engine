"""
Test Groq API Key
==================
Script to verify that the GROQ_API_KEY in .env file is valid and working.
"""

import os
from dotenv import load_dotenv
from groq import Groq

def test_groq_api_key():
    """Test if the GROQ_API_KEY from .env is valid."""
    
    # Load environment variables from .env
    load_dotenv()
    
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("ERROR: GROQ_API_KEY not found in .env file")
        print("Please add your API key to the .env file:")
        print("GROQ_API_KEY=your_actual_groq_api_key_here")
        return False
    
    print(f"API Key found: {api_key[:10]}...{api_key[-4:]}")
    
    # Test the API key
    try:
        client = Groq(api_key=api_key)
        
        # Make a simple API call to test connection
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "Say 'API key is working'"}],
            max_tokens=10
        )
        
        if response and response.choices:
            print("SUCCESS: API key is valid and working")
            print(f"Test response: {response.choices[0].message.content}")
            return True
        else:
            print("ERROR: API call returned empty response")
            return False
            
    except Exception as e:
        print(f"ERROR: API key test failed")
        print(f"   Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Groq API Key...")
    print("=" * 50)
    success = test_groq_api_key()
    print("=" * 50)
    
    if success:
        print("\nYour GROQ_API_KEY is configured correctly!")
        print("You can now run the pipeline.")
    else:
        print("\nPlease check your GROQ_API_KEY in .env file")
        print("Get a new key from: https://console.groq.com/")
