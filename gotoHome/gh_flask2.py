from flask import Flask, render_template, session, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import InputRequired,ValidationError
from flask_googlemaps import GoogleMaps
from werkzeug.contrib.cache import FileSystemCache

from collections import namedtuple

import re

from .scrape_n_class import get_geocode_coords, get_sidewalk_view, classify_image, zip_apt_scraper, \
                    scrape_zillow_data, get_3step_view, my_address_check, get_address_features, get_unit_dets
import os
from .config import flask_secret_key, geocode, zillow

app = Flask(__name__, instance_path='/Users/mrgah/Dropbox/work/code/insight/goto_home/')
app.config['SECRET_KEY'] = flask_secret_key
app.config['GOOGLEMAPS_KEY'] = geocode
GoogleMaps(app)

bootstrap = Bootstrap(app)
moment = Moment(app)

Geocoords = namedtuple('Geocoords','lat lng')

cache = FileSystemCache('cache', default_timeout=(60*60*24))

class AddressForm(FlaskForm):
    # I'd like my custom address validator here, but it keeps throwing errors
    zip = StringField('Please enter a zip code:', [InputRequired()])
    submit = SubmitField('Submit')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

@app.route('/', methods=['GET', 'POST'])
def index():
    form = AddressForm()
    if form.validate_on_submit():
        session['zip'] = form.zip.data
        return redirect(url_for('results'))
    return render_template('index.html', form=form, zip=session.get('zip'))

@app.route('/results')
def results():

    overall_results = {}

    zip_unit_list = zip_apt_scraper(session['zip'], no_listing_pages=1)

    for result in zip_unit_list:

        unit_key, unit_results = get_unit_dets(result)

        overall_results[unit_key] = unit_results

    # session['address_id'] = street_string + '_' + session['address_features']['zip']
    #
    # session['geo_coords'] = get_geocode_coords(session['address'])
    #
    # results[session['address_id']] = get_unit_dets(session['address'])
    #
    #
    # img = session[session['address_id']]['image_name']
    #
    # print("results:\n", session[session['address_id']])

    print("overall results:\n\n", overall_results, "\n\n")

    return render_template('results.html', address=session.get('address'),
                           overall_results=overall_results, zip=session.get('zip'))

@app.route('/about')
def about():
    return render_template('about.html')
