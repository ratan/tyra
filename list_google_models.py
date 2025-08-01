import google.generativeai as genai
import os
from dotenv import load_dotenv


load_dotenv()

# Make sure to set your GOOGLE_API_KEY environment variable
# or replace os.environ.get('GOOGLE_API_KEY') with your key string.
genai.configure(api_key=os.environ.get('GOOGLE_API_KEY'))

print("Available Models for generateContent:")
print("-" * 30)

for m in genai.list_models():
  # The 'generateContent' method is the one used for chat and text generation.
  if 'generateContent' in m.supported_generation_methods:
    print(m.name)