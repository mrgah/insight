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

# import sys
# from io import StringIO
# import tensorflow as tf
# import numpy as np
#
# from label_image import load_graph, read_tensor_from_image_file


# input_address = "3623 Packard St, Parkersburg, WV 26104"

def scrape_zillow_data(input_address):
    session = requests.Session()

    zillow_data = ZillowWrapper()

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
        # "https://www.zillow.com/homedetails/522-S-1200-E-B-Salt-Lake-City-UT-84102/2093097341_zpid/?fullpage=true"

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

# scrape_zillow_data('2502 Leon St #512, Austin, TX 78705')

def get_geocode_coords(input_address):
    params = {'key': , 'address': input_address}

    encoded_query = urlencode(params)

    # print(encoded_query)

    geo_query = "https://maps.googleapis.com/maps/api/geocode/json?" + encoded_query

    http_response = urlopen(geo_query)

    geo_response = http_response.read()

    # geo_response = '{ "results" : [ { "address_components" : [ { "long_name" : "2023", "short_name" : "2023", "types" : [ "street_number" ] }, { "long_name" : "Kentwell Road", "short_name" : "Kentwell Rd", "types" : [ "route" ] }, { "long_name" : "North Mountview", "short_name" : "North Mountview", "types" : [ "neighborhood", "political" ] }, { "long_name" : "Columbus", "short_name" : "Columbus", "types" : [ "locality", "political" ] }, { "long_name" : "Franklin County", "short_name" : "Franklin County", "types" : [ "administrative_area_level_2", "political" ] }, { "long_name" : "Ohio", "short_name" : "OH", "types" : [ "administrative_area_level_1", "political" ] }, { "long_name" : "United States", "short_name" : "US", "types" : [ "country", "political" ] }, { "long_name" : "43221", "short_name" : "43221", "types" : [ "postal_code" ] }, { "long_name" : "1905", "short_name" : "1905", "types" : [ "postal_code_suffix" ] } ], "formatted_address" : "2023 Kentwell Rd, Columbus, OH 43221, USA", "geometry" : { "location" : { "lat" : 40.019841, "lng" : -83.066971 }, "location_type" : "ROOFTOP", "viewport" : { "northeast" : { "lat" : 40.0211899802915, "lng" : -83.06562201970848 }, "southwest" : { "lat" : 40.0184920197085, "lng" : -83.06831998029151 } } }, "place_id" : "ChIJGRAYIAiOOIgRhatypjtzW0s", "types" : [ "street_address" ] } ], "status" : "OK" }'

    json_data = json.loads(geo_response)

    # print(json_data)
    #
    # print(json_data['results'])

    lat = json_data['results'][0]['geometry']['location']['lat']

    lng = json_data['results'][0]['geometry']['location']['lng']

    geo_coords = (lat,lng)

    # print(urlencode({'loc':geo_coords}))

    return geo_coords

# print(get_geocode_coords(input_address))

# dumb_str = (40.019841, -83.066971)

def get_sidewalk_view(input_coords, image_path):
    """ accepts a tuple with coordinates and returns a google streetview image"""

    geo_string = ','.join(map(str,input_coords))
    print(geo_string)

    params = {'size':'1000x1000','location': geo_string , 'pitch': '-20','source':'outdoor'}

    encoded_query = urlencode(params)

    print(encoded_query)

    sidewalk_query = 'https://maps.googleapis.com/maps/api/streetview?' + encoded_query

    print(sidewalk_query)

    http_response = urlopen(sidewalk_query)

    image = http_response.read()

    image_name = encoded_query.replace('&','_') + ".jpg"

    print("image_name",image_name)

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

# get_sidewalk_view(dumb_str)


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

    # result = os.system(command_string, shell=True)

    # input_layer = "input"
    # output_layer = "InceptionV3/Predictions/Reshape_1"
    #
    # graph = load_graph(model_file)
    #
    # input_name = "import/" + input_layer
    # output_name = "import/" + output_layer
    # input_operation = graph.get_operation_by_name(input_name)
    # output_operation = graph.get_operation_by_name(output_name)
    #
    #
    # t = read_tensor_from_image_file(
    #     image_file,
    #     299,
    #     299,
    #     0,
    #     255)
    #
    # output_operation = graph.get_operation_by_name(output_name)
    #
    # with tf.Session(graph=graph) as sess:
    #     with tf.Session(graph=graph) as sess:
    #         results = sess.run(output_operation.outputs[0], {
    #             input_operation.outputs[0]: t
    #         })
    # results = np.squeeze(results)
    #
    # top_k = results.argsort()[-1:]
    # labels = load_labels(label_file)
    # print(labels[0], top_k[0])

# classify_image('moms.jpg','sidewalk_graph.pb','sidewalk_labels.txt')

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

        for link in bsObj.find(class_="paging").findAll("a"):
            if 'href' in link.attrs and link.attrs['href'] != 'javascript:void(0)':

                raw_link = link.attrs['href']
                base_link, new_index, _ = raw_link.rsplit('/', 2)

                if int(new_index) > max_index:
                    max_index = int(new_index)

        return base_link, max_index

    base_link, max_index = get_listings_info(zip)
    print(base_link, max_index)

    new_rentals = []

    for i in range(no_listing_pages):
        time.sleep(random.random())

        try:
            print("requesting page " + str(i + 1) + " of results...")
        except:
            print("problem requesting url")
            pass

        # bsObj = BeautifulSoup(req.text, "lxml")

        try:
            new_locations = bsObj.findAll("div", {"class":"location"})
            for location in new_locations:

                print(location.previous_sibling, location, "\n")
        except:
            pass

        # print(new_locations)

        link_list = []



        print(link_list)

        # locations.append(new_locations)

    # print(locations)

zip_apt_scraper(19146)