from flask import Flask, render_template, session, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import InputRequired,ValidationError
from .scrape_n_class import get_geocode_coords, get_sidewalk_view, classify_image, scrape_zillow_data, get_3step_view
import os

app = Flask(__name__, instance_path='/Users/mrgah/Dropbox/work/code/insight/goto_home/')
app.config['SECRET_KEY'] =

bootstrap = Bootstrap(app)
moment = Moment(app)

def my_address_check(form, field):
    # write address validator for real at some point...
    if len(field.data) < 5:
        raise ValidationError('I suspect ' + field.data + ' is not a complete addresss')

class AddressForm(FlaskForm):
    address = StringField('Please enter an address:', [InputRequired(), my_address_check])
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
    # address = session['address']
    try:
        session['zillow_data'] = scrape_zillow_data(session['address'])
    except:
        pass
    session['geo_coords'] = get_geocode_coords(session['address'])
    # session['geo_coords'] = (40.019841, -83.066971)
    # session['geo_coords'] = (30.2808142,-97.754020799999)
    session['image_name'] = get_sidewalk_view(session['geo_coords'], 'static')

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
