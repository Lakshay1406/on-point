#add pip install --upgrade openai to install requirements
import json,requests
UNSPLASH_ACCESS_KEY = "CVCGyPskgBwfmVDGKRF9EfKb9PqkA29lbictam9smAA"  # Set your Unsplash access key here
# Once you add your API key below, make sure to not share it with anyone! The API key should remain private.
OPENAI_API_KEY="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"
from openai import OpenAI

def search_destinations(start,budget):
  client = OpenAI(api_key=OPENAI_API_KEY)

  completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    response_format={"type":"json_object"},
    messages=[
      {"role": "system", "content": "start fresh.i want the output to be in valid json format the national and international destinations(if applicable) which are under the budget given in rupees by the user and the starting location which is given by user and message to tell any problem occurred or successful . show give me best locations to visit for national and 5 for international if possible no need of descriptions where i can travel with that budget. , all locations should be different from each other, and around india and under budget.if budget is huge then international travel destinations can also be recommended.constraint if budget is less than 8000 then get places within 500km from starting location.if budget is between 8k and 16k then expand to 1000km incremend 500km for every 8k increase in budget.if no international destinations found there should still be a JSON key of int_dest with empty list.the keys in JSON shd be nat_dest,int_dest,message."},
      {"role": "user", "content": start+' '+budget}
    ]
  )

  data=json.loads(completion.choices[0].message.content)
  print(data)
  destinations=data["nat_dest"]+data['int_dest']

  images=[]
  for i in destinations:
    try:
      # Fetch photo of the city from Unsplash
      response = requests.get(
        f"https://api.unsplash.com/search/photos?query={i}&orientation=landscape",
        headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
      )
      response.raise_for_status()  # Raise an exception for HTTP errors
      data = response.json()

      # Extract image URL and user information from the response
      photo = data["results"][0]
      image_urls = photo["urls"]["regular"]
      images+=[image_urls]
    except Exception as e:
      images+=["https://source.unsplash.com/600x900/?tech,street"]
  return destinations, images



