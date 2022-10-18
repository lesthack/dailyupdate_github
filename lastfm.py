from argparse import ArgumentParser
from datetime import datetime, timedelta
from dateutil import tz
import time
from urllib.request import urlopen
import requests
import traceback
import base64
import json
import sys
import os

last_url = 'http://ws.audioscrobbler.com/2.0/'
last_user = None
last_apikey = None

from_zone = tz.gettz('UTC')
to_zone = tz.gettz('America/Mexico_City')
local_now = datetime.now()
local_adjust = local_now - timedelta(hours=1)
#local_date = datetime(local_now.year, local_now.month, local_now.day)
#utc_date = local_date.replace(tzinfo=to_zone).astimezone(from_zone)
#utc_date = (local_now - timedelta(hours=8)).replace(tzinfo=to_zone).astimezone(from_zone)

year = str(local_now.year)
month = str(local_now.month).zfill(2)
day = str(local_now.day).zfill(2)

def scrobbler_hrs(music_path, make_commits=True):
    scrobbler_file = '{base}/{day}.md'.format(base=music_path, day=str(datetime.now().day).zfill(2))
    params = {
        'method': 'user.getRecentTracks',
        'limit': 200,
        'from': int(local_adjust.strftime("%s")),
        'user': last_user,
        'page': 1,
        'api_key': last_apikey,
        'format': 'json'
    }
    try:
        #if os.path.exists(scrobbler_file): os.remove(scrobbler_file)
        r = requests.get(last_url, params=params)
        json_response = json.loads(r.content)
        list_songs = []
        tracks = json_response['recenttracks']['track']
        if type(json_response['recenttracks']['track']) == dict:
            tracks = [json_response['recenttracks']['track']]
        for item in json_response['recenttracks']['track']:
            album = item['album']['#text']
            artist = item['artist']['#text']
            track = item['name']
            date = None
            if 'date' in item.keys():
                utc = datetime.strptime(item['date']['#text'], '%d %b %Y, %H:%M')
                date = utc.replace(tzinfo=from_zone).astimezone(to_zone)
                if len(album) == 0: album = 'unknown'
                if len(artist) == 0: artist = 'unknown'
                if len(track) == 0: track = 'unknown'
                track_info = '{artist}-{album}-{track}|{date}'.format(
                    artist=artist.encode('utf-8'),
                    album=album.encode('utf-8'),
                    track=track.encode('utf-8'),
                    date=date
                ) 
                list_songs.append([date, '{artist} - {album} - {track}'.format(
                    artist=artist.encode('utf-8'),
                    album=album.encode('utf-8'),
                    track=track.encode('utf-8')
                )])
        while list_songs.__len__() > 0:
            item = list_songs.pop()
            sf = open(scrobbler_file, 'a')
            commit_date = item[0].strftime('%Y-%m-%d %H:%M:%S')
            new_line = '{} -> {}'.format(commit_date, item[1])
            sf.write(new_line+'\n')
            sf.close()
            print(new_line)
            if make_commits:
                os.system('export GIT_COMMITTER_DATE="{}"'.format(commit_date))
                os.system('export GIT_AUTHOR_DATE="{}"'.format(commit_date))
                os.system('git add {} -f'.format(scrobbler_file))
                os.system('git commit --date="{}" -m "{}"'.format(commit_date, item[1]))

    except Exception as e:
        print('Error: ', e)
        traceback.print_exc(file=sys.stdout) 

def scrobbler(music_path):
    params = {
        'method': 'user.getRecentTracks',
        'limit': 1,
        'user': last_user,
        'page': 1,
        'api_key': last_apikey,
        'format': 'json'
    }

    try:
        r = requests.get(last_url, params=params)
        json_response = json.loads(r.content)

        album = json_response['recenttracks']['track'][0]['album']['#text']
        artist = json_response['recenttracks']['track'][0]['artist']['#text']
        track = json_response['recenttracks']['track'][0]['name']

        if len(album) == 0: album = 'unknown'
        if len(artist) == 0: artist = 'unknown'
        if len(track) == 0: track = 'unknown'
        
        last_track = ''
        current_track = '{artist} - {album} - {track}'.format(
            artist=artist.encode('utf-8'),
            album=album.encode('utf-8'),
            track=track.encode('utf-8')
        ) 
        scrobbler_file = '{base}/{day}.md'.format(base=music_path, day=str(datetime.now().day).zfill(2))
        if not os.path.isfile(scrobbler_file):
            sf = open(scrobbler_file, 'w')
            sf.write('#Log of {day} day\n\n'.format(day=str(datetime.now().day).zfill(2)))
        else:
            sf = open(scrobbler_file, 'r')
            last_track = str(sf.readlines()[-1][11:-1]).strip()
            sf.close()
            sf = open(scrobbler_file, 'a')
        if last_track != current_track:
            sf.write('1. [{hour}:{minute}] {track}\n'.format(
                hour=str(datetime.now().hour).zfill(2),
                minute=str(datetime.now().minute).zfill(2),
                track=current_track)
            )
        sf.close()
        print(current_track)
    except Exception as e:
        print('Error: ', e)
        traceback.print_exc(file=sys.stdout) 

def topalbums(albums_path):
    params = {
        'method': 'user.getTopAlbums',
        'user': last_user,
        'api_key': last_apikey,
        'format': 'json',
        'period': '6month',
        #'limit': 1,
        #'page': 1,
    }
    list_albums = []
    try:
        r = requests.get(last_url, params=params)
        json_response = json.loads(r.content)
        
        topalbums = json_response['topalbums']
        for album in topalbums['album']:
            img64 = ''
            if(album['image'][2]['#text'].__len__()>0):
                img64 = base64.b64encode(urlopen(album['image'][2]['#text']).read())
            list_albums.append({
                'artist': album['artist']['name'],
                'album': album['name'],
                'url': album['url'],
                'playcount': album['playcount'],
                'image': img64
            })

        sf = open(albums_path, 'w')
        sf.write('{"topalbums":'+json.dumps(list_albums, sort_keys=True, indent=4)+'}')
        sf.close()
        print(len(list_albums))
    except Exception as e:
        print('Error: ', e)
        traceback.print_exc(file=sys.stdout)

argp = ArgumentParser(
    prog='lesthackbot',
        description='Bot for make commits in the repo through scrobbling',
    epilog='GPL v3.0',
    version='2.0'
)
argp.add_argument('-k', dest='api_key', action='store', help='LastFM Api Key')
argp.add_argument('-u', dest='user', action='store', help='LastFM Username')
argp.add_argument('-s', '--scrobbler', action='store_true', help='Scrobbler')
argp.add_argument('-a', '--topalbums', action='store_true', help='Top Albums')
argp.add_argument('-t', '--scrobbler_today', action='store_true', help='Scrobbler Today')
argp.add_argument('-p', dest='path', action='store', help='Path.', default=False)
args = vars(argp.parse_args())

if args['api_key'] and args['user']:
    last_apikey = args['api_key']
    last_user = args['user']
if last_apikey and last_user and args['path'] and args['scrobbler']:
    music_path = os.path.join(args['path'], 'music', year, month)
    scrobbler(music_path)
elif last_apikey and last_user and args['scrobbler_today']:
    music_path = os.path.join(args['path'], 'music', year, month)
    if not os.path.exists(music_path): os.makedirs(music_path)
    scrobbler_hrs(music_path)
elif last_apikey and last_user and args['path'] and args['topalbums']:
    topalbums(args['path'])
else:
    argp.print_help()

