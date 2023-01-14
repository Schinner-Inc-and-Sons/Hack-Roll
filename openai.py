import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

response = openai.Completion.create(model="text-davinci-003", prompt="{{TEXT_INPUT}}", temperature=0, max_tokens=100)