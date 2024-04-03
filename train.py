import requests

def get_city_from_address(address,rapid_api_key):


    url = "https://address-from-to-latitude-longitude.p.rapidapi.com/geolocationapi"

    querystring = {"address": address}

    headers = {
        "X-RapidAPI-Key": rapid_api_key,
        "X-RapidAPI-Host": "address-from-to-latitude-longitude.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)

    return(response.json()['Results'][0]['city'])

def get_tickets_from_stcode(start,end,date,rapid_api_key):


    url = "https://irctc1.p.rapidapi.com/api/v3/trainBetweenStations"

    querystring = {"fromStationCode": start, "toStationCode": end, "dateOfJourney": date}

    headers = {
        "X-RapidAPI-Key": rapid_api_key,
        "X-RapidAPI-Host": "irctc1.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)
    print(response.json())
    data=response.json()['data']
    i=len(data)
    j=0
    l=[]
    train_details={}
    while i>0 and j<=3:
        train_details["train_number"]=data[j]["train_number"]
        train_details["train_name"] = data[j]["train_name"]
        train_details["duration"] = data[j]["duration"]
        train_details["from"] = data[j]["from"]
        train_details["to"] = data[j]["to"]
        train_details["departure_time"] = data[j]["from_sta"]
        train_details["arrival_time"] = data[j]["to_sta"]
        train_details["from_station_name"] = data[j]["from_station_name"]
        train_details["to_station_name"] = data[j]["to_station_name"]


        url = "https://irctc1.p.rapidapi.com/api/v2/getFare"

        querystring = {"trainNo": train_details["train_number"], "fromStationCode": train_details["from"], "toStationCode": train_details["to"]}

        headers = {
            "X-RapidAPI-Key": rapid_api_key,
            "X-RapidAPI-Host": "irctc1.p.rapidapi.com"
        }

        sss = requests.get(url, headers=headers, params=querystring)
        print(sss.json())
        d=sss.json()['data']["general"][0]
        train_details["class"]=d["classType"]
        train_details["fare"]=d["fare"]


        l+=[train_details]

        train_details = {}
        i-=1
        j+=1
    print()
    print(l)

start='MAS'
end='SBC'
date='2024-04-03'
rapid_api_key='23f0a5b85cmsh83140e0a39e0664p11dbefjsnd7193ad7a38b'
get_tickets_from_stcode(start,end,date,rapid_api_key)

