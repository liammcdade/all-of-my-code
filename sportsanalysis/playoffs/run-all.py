


import requests

url = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.2/scoreboard"
data = requests.get(url).json()

fixtures = []
for event in data["events"]:
    home = event["competitions"][0]["competitors"][0]["team"]["displayName"]
    away = event["competitions"][0]["competitors"][1]["team"]["displayName"]
    fixtures.append((home, away))

print(fixtures)