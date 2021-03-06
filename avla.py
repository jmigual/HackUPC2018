
# coding: utf-8

# In[192]:


import requests
import json
import time


def get_token():
    with open("token.key") as f:
        return f.readline().replace("\n", "")


TOKEN = get_token()


def add_id(url):
    url += '&client_id=' + TOKEN
    return url


def get_lab_buildings():
    labs_url = 'https://api.fib.upc.edu/v2/laboratoris/?format=json'
    labs = requests.get(add_id(labs_url)).json()
    return labs['imatges'].keys()


def lab_image(building):
    labs_url = 'https://api.fib.upc.edu/v2/laboratoris/?format=json'
    labs = requests.get(add_id(labs_url)).json()
    
    image_url = labs['imatges'][building]
    return add_id(image_url)


# Returns available and unavailable dictionaries given a building
# available dict: {'class_id':(available_pcs, date_hour_limit)}
# unavailable dict: {'class_id':(class_happening, date_hour_limit)}

def lab_stats(building):
    labs_url = 'https://api.fib.upc.edu/v2/laboratoris/?format=json'
    labs = requests.get(add_id(labs_url)).json()
    
    time_format = '%Y-%m-%dT%H:%M:%S'
    inici = '&data_inici=' + time.strftime('%Y-%m-%d')

    available = {}
    unavailable = {}

    for avla in labs['results']:
        places = avla['places_disponibles']
        if places != None and places > 0 and avla['id'][:2] == building:
            date = ''
            reserves = requests.get(add_id(avla['reserves'])+inici).json()
            
            if len(avla['reserves_actuals']) == 0:
                for res in reserves['results']:
                    ini = time.strptime(res['inici'], time_format)
                    if time.mktime(ini) > time.time():
                        if ini.tm_mday == time.localtime().tm_mday:
                            date = time.strftime('%H:%M',ini)
                        break

                available[avla['id']] = (avla['places_disponibles'], date)
                
            else:
                for res in reserves['results']:
                    fi = time.strptime(res['fi'], time_format)
                    if time.mktime(fi) > time.time():
                        if fi.tm_mday == time.localtime().tm_mday:
                            date = time.strftime('%H:%M',fi)
                        break

                unavailable[avla['id']] = (res['titol'], date)
    return available, unavailable

