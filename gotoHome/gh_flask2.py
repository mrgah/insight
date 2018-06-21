from flask import Flask, render_template, session, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import InputRequired,ValidationError
from flask_googlemaps import GoogleMaps
from werkzeug.contrib.cache import FileSystemCache

from collections import namedtuple

from .scrape_n_class import get_geocode_coords, get_sidewalk_view, classify_image, \
                    scrape_zillow_data, get_3step_view, my_address_check, get_address_features
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
    address = StringField('Please enter an address:', [InputRequired()])
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
        session['address'] = form.address.data
        return redirect(url_for('results'))
    return render_template('index.html', form=form, address=session.get('address'))

@app.route('/results')
def results():
    session['address_features'] = get_address_features(session['address'], 'street_address', 'city', 'state', 'zip')

    session['address_id'] = re.sub(r'\s+', '_', session['address_features']['street_address'].strip()).lower() + '_' + [session['zip'] + '.jpg'

    try:
        session['zillow_data'] = scrape_zillow_data(session['address'])
    except:
        pass
    session['geo_coords'] = get_geocode_coords(session['address'])
    # session['geo_coords'] = (40.019841, -83.066971)
    # session['geo_coords'] = (30.2808142,-97.754020799999)
    session['image_name'] = get_sidewalk_view(session['geo_coords'], 'static', session['address_features'])

    session['step_image_name'] = get_3step_view(session['geo_coords'])

    img = session['image_name']
    print("session['image_name']",session['image_name'])
    image_path = os.path.join('static', img)
    session['sidewalk_class_result'] = classify_image(image_path, 'sidewalk_graph.pb', 'sidewalk_labels.txt')

    img = session['step_image_name']
    print("session['step_image_name']",session['step_image_name'])
    image_path = os.path.join('static', img)

    session['3_steps_result'] = classify_image(image_path, '3steps_graph.pb','3steps_labels.txt')

    return render_template('results.html', address=session.get('address'), geo_coords=session.get('geo_coords'),
                           sidewalk_class_result=session.get('sidewalk_class_result'), img=session.get('image_name'),
                           zillow_data=session.get('zillow_data'), steps=session.get('3_steps_result'))

@app.route('/about')
def about():
    return render_template('about.html')
