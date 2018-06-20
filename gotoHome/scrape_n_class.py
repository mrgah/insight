import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from urllib.request import urlopen

import random
import time

import json

import os
from subprocess import Popen,PIPE,STDOUT

import re
from pyzillow.pyzillow import ZillowWrapper, GetDeepSearchResults

import config

def my_address_check(address_maybe):

    street_re = re.compile(r'[-\d]+ [\w\s]+')

    state_zip_re = re.compile(r'[A-Z]{2} \d{5}')

    address_list = address_maybe.split(',')

    if re.match(street_re, address_list[0].strip()) and re.match(state_zip_re, address_list[2].strip()):
        print(address_maybe.strip(), "looks like an address")
        return True

    else:
        print("hmm...", address_maybe.strip(), "does not appear to be a full address")
        return False




def scrape_zillow_data(input_address):
    session = requests.Session()

    zillow_data = ZillowWrapper(config.zillow)

    m = re.search(r'[0-9]{5}',input_address)

    zipcode = m.group(0)
    print("ZIP code: ", zipcode)

    deep_search_response = zillow_data.get_deep_search_results(input_address,zipcode)
    result = GetDeepSearchResults(deep_search_response)
    zillow_id = result.zillow_id
    print("Zillow ID: ", zillow_id)

    headers = { "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit 537.36 (KHTML, like Gecko) Chrome",
        "Accept": "text/html,application/xhtml+xml,application/xml; q=0.9,image/webp,*/*;q=0.8"}

    url = "https://www.zillow.com/homedetails/" + zillow_id + "_zpid/?fullpage=true"

    facts = {}

    try:
        req = session.get(url, headers=headers)
    except:
        pass

    bsObj = BeautifulSoup(req.text, "lxml")

    facts['unit_type'] = bsObj.find(class_="hdp-fact-ataglance-value").get_text()


    try:
        unit_facts = bsObj.find("div", {"class": "hdp-fact-container"}).find_all("li")
        print(unit_facts)

        for fact in unit_facts:
            fact_name = fact.span.get_text()
            try:
                fact_value = fact.span.nextSibling.get_text()
            except:
                fact_value = ""
                pass
            print(fact_name, fact_value)
    except:
        print("could not find out unit facts")

    try:
        unit_dates = bsObj.find(text="Dates").parent.nextSibling.find_all("li")
        for date in unit_dates:
            m = re.search(r'[12][0-9]{3}', date.get_text())
            # print(m.group(0))
            facts['dates'] = m.group(0)
    except:
        print("could not find information on unit dates")

    try:
        hdp_amen2_facts = bsObj.find(text="Amenities").parent.nextSibling.find_all("li")
        amenities = []
        for fact in hdp_amen2_facts:
            amenities.append(fact.get_text())

            # print(fact.get_text())
        facts['amenities'] = amenities
    except:
        print("could not find information on unit amenities")

    print(facts)

    return facts

def get_geocode_coords(input_address):
    params = {'key': config.geocode, 'address': input_address}

    encoded_query = urlencode(params)

    geo_query = "https://maps.googleapis.com/maps/api/geocode/json?" + encoded_query

    http_response = urlopen(geo_query)

    geo_response = http_response.read()

    json_data = json.loads(geo_response)

    lat = json_data['results'][0]['geometry']['location']['lat']

    lng = json_data['results'][0]['geometry']['location']['lng']

    geo_coords = (lat,lng)

    return geo_coords

def get_sidewalk_view(input_coords, image_path):
    """ accepts a tuple with coordinates and returns a google streetview image"""

    geo_string = ','.join(map(str,input_coords))
    print(geo_string)

    params = {'size':'1000x1000','location': geo_string , 'pitch': '-20', 'source':'outdoor'}

    encoded_query = urlencode(params)

    print(encoded_query)

    sidewalk_query = 'https://maps.googleapis.com/maps/api/streetview?' + encoded_query

    print(sidewalk_query)

    http_response = urlopen(sidewalk_query)

    image = http_response.read()

    image_name = encoded_query.replace('&', '_') + ".jpg"

    print("image_name", image_name)

    image_full_path = os.path.join(image_path, image_name)

    with open(image_full_path,'wb') as f:
        f.write(image)

    return image_name

def get_3step_view(input_coords):
    """ accepts a tuple with coordinates and returns a google streetview image"""

    geo_string = ','.join(map(str,input_coords))
    print(geo_string)

    params = {'size':'1000x1000','location': geo_string , 'pitch': '-10', 'fov':'50', 'source':'outdoor'}

    encoded_query = urlencode(params)

    print(encoded_query)

    sidewalk_query = 'https://maps.googleapis.com/maps/api/streetview?' + encoded_query

    print(sidewalk_query)

    http_response = urlopen(sidewalk_query)

    image = http_response.read()

    image_name = encoded_query.replace('&','_') + ".jpg"

    print("image_name",image_name)

    image_path = "static/" + image_name

    with open(image_path,'wb') as f:
        f.write(image)

    return image_name


def classify_image(image_file,model_file,output_labels='output_labels.txt'):

    command_string = 'python label_image.py --graph=' + model_file + ' --labels=' + output_labels + ' --input_layer=Placeholder --output_layer=final_result --image=' + image_file

    command = 'python '
    command_args = 'label_image.py --graph=' + model_file + ' --labels=' + output_labels + ' --input_layer=Placeholder --output_layer=final_result --image=' + image_file

    print(command_string)

    proc = Popen(command + command_args, shell=True, stdout=PIPE)
    output = proc.communicate()[0].decode()
    result = re.split(r'\n',output)[0]
    print(result)
    return result


def zip_apt_scraper(zip, no_listing_pages=5):

    rentals = []

    headers = { "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit 537.36 (KHTML, like Gecko) Chrome",
        "Accept": "text/html,application/xhtml+xml,application/xml; q=0.9,image/webp,*/*;q=0.8"}

    session = requests.Session()

    def get_listings_info(zip):
        first_link = "https://www.apartments.com/brooklyn-ny-" + str(zip) + "/"

        try:
            print("requesting first page...")
            req = session.get(first_link, headers=headers)

            bsObj = BeautifulSoup(req.text, "lxml")

            print("success")

        except:
            print("requesting first page failed...")
            pass

        max_index = 1

        try:
            for link in bsObj.find(class_="paging").findAll("a"):
                if 'href' in link.attrs and link.attrs['href'] != 'javascript:void(0)':

                    raw_link = link.attrs['href']
                    base_link, new_index, _ = raw_link.rsplit('/', 2)

                    if int(new_index) > max_index:
                        max_index = int(new_index)
        except:
            print("could not find paging links")
            raise

        return base_link, max_index

    base_link, max_index = get_listings_info(zip)
    print(base_link, max_index)

    new_rentals = []

    for i in range(no_listing_pages):
        time.sleep(random.random())

        # link = base_link + "/" + str(i) + "/"

        link = '/'.join([base_link, str(i + 1)])
        print(link)

        try:
            print("requesting page " + str(i + 1) + " of results...")
            req = session.get(link, headers=headers)
        except:
            print("problem requesting url")
            pass

        bsObj = BeautifulSoup(req.text, "lxml")

        try:
            new_locations = bsObj.findAll("div", {"class": "location"})
            for location in new_locations:
                if my_address_check(location.get_text()):
                    new_rentals.append(location.get_text())

                # location.previous_sibling
        except:
            print("could not find location elements...")
            pass

        rentals.extend(new_rentals)

    return rentals

zip_apt_scraper(19146)