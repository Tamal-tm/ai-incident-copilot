import os
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents="An alert fired: HighErrorBudgetBurn on service-a, 5xx rate 12% over 5 minutes. "
             "In 2-3 sentences, suggest the most likely cause and first diagnostic step.",
)
print(response.text)
