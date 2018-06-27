import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from urllib.request import urlopen

import random
import time

import json

from collections import namedtuple

import os
from subprocess import Popen,PIPE

import re

from imageio import imread

from pyzillow.pyzillow import ZillowWrapper, GetDeepSearchResults

from .config import zillow, geocode, onboard_key

Geocoords = namedtuple('Geocoords','lat lng')



def get_address_features(input_address, *args):

    address_features = {}

    address_match_groups = {
        'street_address' : 'street_match.group(0)',
        'house_no' : 'street_match.group(1)',
        'street_name' : 'street_match.group(2)',
        'city' : 'city_match.group(0)',
        'state' : 'state_match.group(0)',
        'zip' : 'zip_match.group(0)'
    }

    address_list = input_address.split(',')

    street_re = re.compile(r'([-\d]+) ([\w\s]+)')

    city_re = re.compile(r'[\w\s]+')

    state_zip_re = re.compile(r'([A-Za-z]{2}) (\d{5})')

    state_re = re.compile(r'[A-Za-z]{2}')

    zip_re = re.compile(r'(\d{5}|\d{5}-\d{4})')

    street_match = re.search(street_re, address_list[0].strip())

    # the following blocks seem a little crufty and redundant to me, but I can't think of a good way to refactor...
    try:
        city_match = re.search(city_re, address_list[1].strip())
        state_zip_match = re.search(state_zip_re, address_list[2].strip())

    except:
        print("no city found")
        pass

    try:
        state_match = re.search(state_re, address_list[-1].strip())

    except:
        print("no state found")
        pass

    try:
        zip_match = re.search(zip_re, address_list[-1].strip())
    except:
        print("no zip code found")
        pass

    for arg in args:
        if arg not in address_match_groups.keys():
            raise
        try:
            address_features[arg] = eval(address_match_groups[arg])

        except:
            address_features[arg] = ''
            pass

    return address_features

def my_address_check(address_maybe):

    address_features = get_address_features(address_maybe, 'street_address', 'city', 'state', 'zip')

    if address_features['street_address'] and (address_features['zip'] or
                                               (address_features['city'] and address_features['state'])):
        print(address_maybe.strip(), "looks like an address")
        return True

    else:
        print("hmm...", address_maybe.strip(), "does not appear to be a full address")
        return False

def scrape_zillow_data(input_address):
    session = requests.Session()

    zillow_data = ZillowWrapper(zillow)

    m = re.search(r'[0-9]{5}',input_address)

    zipcode = m.group(0)
    # print("ZIP code: ", zipcode)

    deep_search_response = zillow_data.get_deep_search_results(input_address,zipcode)
    result = GetDeepSearchResults(deep_search_response)
    zillow_id = result.zillow_id
    # print("Zillow ID: ", zillow_id)

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

            print("amenities:", fact.get_text())
        facts['amenities'] = amenities
    except:
        print("could not find information on unit amenities")

    print(facts)

    return facts

def get_geocode_coords(input_address):
    params = {'key': geocode, 'address': input_address}

    Geocoords = namedtuple('Geocoords', 'lat lng')

    encoded_query = urlencode(params)

    geo_query = "https://maps.googleapis.com/maps/api/geocode/json?" + encoded_query

    http_response = urlopen(geo_query)

    geo_response = http_response.read()

    json_data = json.loads(geo_response)

    lat = json_data['results'][0]['geometry']['location']['lat']

    lng = json_data['results'][0]['geometry']['location']['lng']

    geo_coords = Geocoords(lat, lng)

    return geo_coords

def is_img_blank(img_name):
    im = imread(img_name, pilmode='RGB')
    img_x, img_y = im.shape[0], im.shape[1]
    trues = 0
    falses = 0
    for i in range(100):
        x = random.randint(0, (img_x-1))
        y = random.randint(0, (img_y-1))
        color = tuple(im[x][y])
        if color == (228, 227, 223):
            trues = trues + 1
        else:
            falses = falses + 1
    if (falses/(trues + falses) > .05):
        return False
    else:
        return True

def get_sidewalk_view(input_coords, image_path, address_features):
    """ accepts a tuple with coordinates and returns a google streetview image"""

    geo_string = ','.join(map(str, input_coords))
    print(geo_string)

    params = {'size':'1000x1000', 'location': geo_string , 'pitch': '-20', 'source':'outdoor'}

    encoded_query = urlencode(params)

    print(encoded_query)

    sidewalk_query = 'https://maps.googleapis.com/maps/api/streetview?' + encoded_query

    print(sidewalk_query)

    http_response = urlopen(sidewalk_query)

    image = http_response.read()

    # image_name = encoded_query.replace('&', '_') + ".jpg"

    encoded_street_address = re.sub(r'\s+', '_', address_features['street_address'])

    image_name = encoded_street_address + '_' + address_features['zip'] + '.jpg'

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

                # ok, this else block breaks this for loop in some crucial way, but I'd still like to glean
                # the results that aren't in the location attrib...
                # else:
                #     print("else", location)
                #     listing_list = bsObj.find("placardContainer").findAll("a")
                #     print(listing_list)

                # location.previous_sibling
        except:
            print("could not find location elements...")
            pass

        rentals.extend(new_rentals)

    # the value the following line prints out is incorrect (doubled?)
    print("the number of rentals this search found is", len(rentals))

    return rentals

def get_unit_dets(address):

    results = {}

    results['address_features'] = get_address_features(address, 'street_address', 'city', 'state', 'zip')

    street_string = re.sub(r'\s+', '_', results['address_features']['street_address'].strip()).lower()

    address_id = street_string + '_' + results['address_features']['zip']

    try:
        results['zillow_data'] = scrape_zillow_data(address)
    except:
        print("could not scrape zillow data for", address)
        pass

    results['levels'], results['proptype'], results['yearbuilt'] = get_onboard_prop_details(address)

    results['geo_coords'] = get_geocode_coords(address)

    # this is a little clunky, but will be replaced
    results['image_name'] = get_sidewalk_view(results['geo_coords'], 'static', results['address_features'])



    # also clunky and inconsistent
    results['step_image_name'] = get_3step_view(results['geo_coords'])

    img = results['image_name']
    print("results['image_name']", results['image_name'])
    image_path = os.path.join('static', img)

    # results['blank_img'] = is_img_blank(image_path)

    # # if results['blank_img'] == True:
    #     results['sidewalk_class_result'] = None
    #     results['3_steps_result'] = None
    # else:

    # tried to assess whether images where blank, but ended up in dependency hell (but see is_img_blank.ipynb)
    results['sidewalk_class_result'] = classify_image(image_path, 'sidewalk_graph.pb', 'sidewalk_labels.txt').split(
        ' ')
    results['3_steps_result'] = classify_image(image_path, '3steps_graph.pb', '3steps_labels.txt').split(' ')

    try:
        results['access_grade'], results['access_label'] = assess_unit_accessibility(results)
    except:
        results['access_grade'], results['access_label'] = 'unknown', 'unknown'
        pass

    return address_id, results

def assess_unit_accessibility(results):
    access_grade = 35

    zillow_data = results.get('zillow_data', {'dates': 0, 'unit_type': None, 'amenities': []})
    print(zillow_data['dates'])

    if results['sidewalk_class_result'][0] == 'yes':
        print("sidewalk")
        access_grade = access_grade + 10
    elif results['sidewalk_class_result'][0] == 'no':
        print("no sidewalk")
        access_grade = access_grade - 10

    if results['3_steps_result'][0] == 'no':
        print("few steps")
        access_grade = access_grade + 15
    elif results['3_steps_result'][0] == 'yes':
        print("lots of steps")
        access_grade = access_grade - 15

    if ((results['proptype'] in ['APARTMENT', 'MULTI FAMILY DWELLING']
         or zillow_data['unit_type'] in ['Apartment', 'Condo'])
            and int(zillow_data.get('dates', 0)) > 2000 or int(results['yearbuilt']) > 2000):
        print("newer building")
        access_grade = access_grade + 20

    if ((results['proptype'] in ['APARTMENT', 'MULTI FAMILY DWELLING']
         or zillow_data['unit_type'] in ['Apartment', 'Condo'])
            and (int(zillow_data.get('dates', 0)) < 2000 and int(zillow_data.get('dates', 0)) > 1980
                 or int(results['yearbuilt']) < 2000 and int(results['yearbuilt']) > 1980)):
        print("reasonably modern building")
        access_grade = access_grade + 10

    if ((results['proptype'] in ['APARTMENT', 'MULTI FAMILY DWELLING']
         or zillow_data['unit_type'] in ['Apartment', 'Condo'])
            and (int(zillow_data.get('dates', 0)) < 1980 and int(zillow_data.get('dates', 0) > 1700)
                 or (int(results['yearbuilt']) < 1980 and int(results['yearbuilt']) > 1700))):
        print("old building")
        access_grade = access_grade - 5

    if (results.get('levels', .5) > 1) and 'Elevator' in zillow_data.get('amenities', []):
        print("multi story, elevator")
        access_grade = access_grade + 5

    if (results.get('levels', .5) > 1) and 'Elevator' not in zillow_data.get('amenities', []):
        print("multi story, no elevator")
        access_grade = access_grade - 5

    if access_grade >= 80:
        access_label = 'great'
    elif access_grade < 80 and access_grade > 59:
        access_label = 'good'
    elif access_grade < 59 and access_grade > 29:
        access_label = 'fair'
    elif access_grade < 29:
        access_label = 'poor'

    return access_grade, access_label

def get_onboard_prop_details(input_address):
    # at the moment, this simply returns the number of levels in a building
    headers = {'Accept': 'application/json', 'apikey': onboard_key}

    params = {'address': input_address}

    encoded_query = urlencode(params)

    onboard_query = "https://search.onboard-apis.com/propertyapi/v1.0.0/property/detail?" + encoded_query

    session = requests.Session()

    try:
        req = session.get(onboard_query, headers=headers)

        json_data = json.loads(req.text)

        levels = json_data['property'][0]['building']['summary']['levels']

        proptype = json_data['property'][0]['summary']['proptype']

        yearbuilt = json_data['property'][0]['building']['summary']['yearbuilt']


    except:
        levels = 0
        proptype = None
        yearbuilt = 0
        pass

    return levels, proptype, yearbuilt
