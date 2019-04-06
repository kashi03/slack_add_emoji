
import os
import re
import requests
import json
import io
from bs4 import BeautifulSoup

from  flask import Flask, request, Response, jsonify

URL_CUSTOMIZE = "https://{team_name}.slack.com/customize/emoji"
URL_ADD = "https://{team_name}.slack.com/api/emoji.add"
URL_LIST = "https://{team_name}.slack.com/api/emoji.adminList"

API_TOKEN_REGEX = r"\"api_token\":\"(.*)\",\"hc_tracking_qs"
API_TOKEN_PATTERN = re.compile(API_TOKEN_REGEX)

def session(team_name, cookie):
    session = requests.session()
    session.headers = {'Cookie': cookie}
    session.url_customize = URL_CUSTOMIZE.format(team_name=team_name)
    session.url_add = URL_ADD.format(team_name=team_name)
    session.url_list = URL_LIST.format(team_name=team_name)
    session.api_token = _fetch_api_token(session)
    return session

def _fetch_api_token(session):
    # Fetch the form first, to get an api_token.
    r = session.get(session.url_customize)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    all_script = soup.findAll("script")
    for script in all_script:
        for line in script.text.splitlines():
            if 'api_token' in line:
                # api_token: "xoxs-12345-abcdefg....",
                return API_TOKEN_PATTERN.search(line.strip()).group(1)

    raise Exception('api_token not found. response status={}'.format(r.status_code))
    return 'api_token not found. response status={}'.format(r.status_code)

def upload_emoji(session, emoji_name, filename):
    data = {
        'mode': 'data',
        'name': emoji_name,
        'token': session.api_token
    }


    # files = {'image': open(filename, 'rb')}
    img = requests.get(filename).content
    files = {'image': img}
    r = session.post(session.url_add, data=data, files=files, allow_redirects=False)
    r.raise_for_status()

    # Slack returns 200 OK even if upload fails, so check for status.
    response_json = r.json()
    if not response_json['ok']:
        print("Error with uploading %s: %s" % (emoji_name, response_json))
        return False
    else:
        return True

app = Flask(__name__)

@app.route('/add_emoji', methods=['POST'])
def index():
    text = request.form['text'].split()
    if not len(text) == 2:
        return jsonify(text='コマンドが間違っています。確認してください。', response_type='in_channel') 
    
    team_name = ''
    cookie = ''

    with open('myconf.json', 'r') as f:
        info = json.load(f)
        team_name = info['team_name']
        cookie = info['cookie']
    
    s = session(team_name, cookie)
    r = upload_emoji(s, text[0], text[1])
    if r:
        return jsonify(text=f':{text[0]}:({text[0]})を追加しました。', response_type='in_channel') 
    else:
        return jsonify(text='絵文字の追加に失敗しました。', response_type='in_channel') 
    return f'index() {request.method}'

if __name__ == "__main__":
    # team_name = ''
    # cookie = ''

    # with open('conf.json', 'r') as f:
    #     info = json.load(f)
    #     team_name = info['team_name']
    #     cookie = info['cookie']
    
    # s = session(team_name, cookie)
    # upload_emoji(s, 'google', 'https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png')
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))