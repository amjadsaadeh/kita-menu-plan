import base64
import os
import json
import logging
import datetime
import functools

from flask import Flask, request, session, render_template, url_for, redirect, flash
from authlib.integrations.flask_client import OAuth

from google.cloud import firestore, storage
import google.auth.credentials


BUCKET_NAME = 'kita-menu-images'


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
oauth = OAuth(app)

db = firestore.Client()

oauth.register(
    name='amazon',
    client_kwargs={
        'scope': 'profile'
    },
    client_id=os.environ.get('AMAZON_CLIENT_ID'),
    client_secret=os.environ.get('AMAZON_CLIENT_SECRET'),
    #request_token_url='https://www.amazon.com/ap/oa',
    access_token_url='https://api.amazon.com/auth/o2/token',
    authorize_url='https://www.amazon.com/ap/oa'
)


def login_required(func: callable) -> callable:
    """
    decorator for login enforcement

    Parameters
    ----------
    func : callable
        function to decorate

    Returns
    -------
    callable
        decorated function
    """
    @functools.wraps(func)
    def login_req_func(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('login')
        return func(*args, **kwargs)
    return login_req_func



@app.route('/', methods=['GET'])
@login_required
def index():    
    doc_ref = db.collection(u'menus').document(session['user_id'])
    doc = doc_ref.get().to_dict()
    if doc is None:
        doc_ref.create({'cw': datetime.datetime.now().isocalendar()[1], 'menu': {}})

    return render_template('index.html', menu=doc['menu'])

@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')

@app.route('/auth/amazon', methods=['GET'])
def amazon_auth():
    redirect_uri = url_for('amazon_auth_finished', _external=True)
    return oauth.amazon.authorize_redirect(redirect_uri)

@app.route('/auth/finished', methods=['GET'])
def amazon_auth_finished():
    token = oauth.amazon.authorize_access_token()
    resp = oauth.amazon.get('https://api.amazon.com/user/profile', token=token)
    profile = resp.json()
    session['user_id'] = profile['user_id']
    session['name'] = profile['name']
    # do something with the token and profile
    return redirect(url_for('index'))

@app.route('/logout', methods=['GET'])
@login_required
def logout():
    session.pop('user_id', None)
    session.pop('name', None)
    return redirect(url_for('login'))

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[-1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if 'user_id' not in session:
        return redirect('login')

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            file_ext = file.filename.rsplit('.', 1)[-1].lower()
            file.save('tmp.{:s}'.format(file_ext))
            client = storage.Client()
            bucket = client.bucket(BUCKET_NAME)
            blob = bucket.blob('{:s}.{:s}'.format(session['user_id'], file_ext))
            blob.upload_from_filename('tmp.{:s}'.format(file_ext))
            return redirect(url_for('index'))
    return redirect(url_for('index'))
    

if __name__ == '__main__':
    PORT = int(os.getenv('PORT')) if os.getenv('PORT') else 8080
    app.run(host='127.0.0.1', port=PORT, debug=True)