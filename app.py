#!/usr/bin/env python
from flask import Flask, abort, request, render_template
from uuid import uuid4
import requests
import requests.auth
import urllib
import urllib.parse
import time
from dotenv import load_dotenv
import os
from supabase import create_client, Client

FIELDNAMES = ['username', 'message']

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)


def user_agent():
    '''flask app by u/UnemployedTechie2021
    '''
    return 'flask app by u/UnemployedTechie2021'


def base_headers():
    return {"User-Agent": user_agent()}


app = Flask(__name__)


@app.route('/')
def homepage():
    authorize_url = make_authorization_url()
    return render_template('index.html', authorize_url=authorize_url)


@app.route('/reddit_callback')
def reddit_callback():
    error = request.args.get('error', '')
    if error:
        return "Error: " + error
    state = request.args.get('state', '')
    if not is_valid_state(state):
        # Uh-oh, this request wasn't started by us!
        abort(403)
    code = request.args.get('code')
    access_token = get_token(code)
    username = get_username(access_token)

    # Check if username already exists
    result = supabase.table('secret_santa').select('*').eq('username', username).execute()
    if (result.data):
        user_exists = "1"
        temp_gift = result.data[0]['gift']
        temp_santa_gift = result.data[0]['santa_gift']
        santa_username = result.data[0]['santa_username']
        santa_message = result.data[0]['santa_message']
        if not temp_santa_gift:
            santa_gift = "No gift from Santa yet"
        else:
            santa_gift = temp_santa_gift
        if not temp_gift:
            gift = ""
        else:
            gift = temp_gift
    else:
        user_exists = "0"
        santa_gift = "You are not registered for Secret Santa. Better luck next year!"
        santa_username = ""
        gift = ""
        santa_message = ""

    return render_template('index.html', username=username, user_exists=user_exists, santa_gift=santa_gift, santa_username=santa_username, gift=gift, santa_message=santa_message)

@app.route('/submit', methods=['POST'])
def submit_data():
    username = request.form.get('username')
    gift = request.form.get('gift')
    santa_username = request.form.get('santa_username')
    # Insert data into Supabase table
    supabase.table('secret_santa').update({'gift': gift}).eq('username', username).execute()
    supabase.table('secret_santa').update({'santa_gift': gift}).eq('username', santa_username).execute()
    success_message = "Gift sent 🎁🎅🏻�❄️"

    return render_template('success.html', username=username, success_message=success_message)

def make_authorization_url():
    # Generate a random string for the state parameter
    # Save it for use later to prevent xsrf attacks
    state = str(uuid4())
    save_created_state(state)
    params = {"client_id": CLIENT_ID,
              "response_type": "code",
              "state": state,
              "redirect_uri": REDIRECT_URI,
              "duration": "temporary",
              "scope": "identity"}
    url = "https://ssl.reddit.com/api/v1/authorize?" + urllib.parse.urlencode(params)
    return url


# Left as an exercise to the reader.
# You may want to store valid states in a database or memcache.
def save_created_state(state):
    pass


def is_valid_state(state):
    return True


def get_token(code):
    client_auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    post_data = {"grant_type": "authorization_code",
                 "code": code,
                 "redirect_uri": REDIRECT_URI}
    headers = base_headers()
    response = requests.post("https://ssl.reddit.com/api/v1/access_token",
                             auth=client_auth,
                             headers=headers,
                             data=post_data)
    token_json = response.json()
    return token_json["access_token"]


def get_username(access_token):
    headers = base_headers()
    headers.update({"Authorization": "bearer " + access_token})
    response = requests.get("https://oauth.reddit.com/api/v1/me", headers=headers)
    me_json = response.json()

    username = me_json['name']

    return username


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=65010, debug=True)
