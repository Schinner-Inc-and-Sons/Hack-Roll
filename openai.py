import openai

OPENAI_API_KEY = ""
openai.api_key = OPENAI_API_KEY

#response = openai.Completion.create(model="text-davinci-003", prompt="{{TEXT_INPUT}}", max_tokens=7)

def getSummary(prompt,maxlimit=50,randomness=0,model="text-davinci-003"):
    response=openai.Completion.create(model=model, prompt='Summarise this "'+prompt+'"', temperature = randomness, max_tokens=maxlimit)
    return response.choices[0].text

