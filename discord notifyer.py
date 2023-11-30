import discord
import os
import requests
import json
from dotenv import load_dotenv
import asyncio
import base64
import datetime
import random

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
API_KEY = os.getenv('API_KEY')
channel_ids = os.getenv('CHANNEL_IDS').split(',')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPO_OWNER = 'godotengine'
REPO_NAME = 'godot'
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_USER_TOKEN = os.getenv('SPOTIFY_USER_TOKEN')

intents = discord.Intents.default()
client = discord.Client(intents=intents)


def check_new_branches():
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    response = requests.get(f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/branches', headers=headers)
    data = response.json()
    latest_branch = data[0]['name']

    if os.path.exists('latest_branch.txt'):
        with open('latest_branch.txt', 'r') as file:
            stored_branch = file.read().strip()
    else:
        stored_branch = None

    if latest_branch != stored_branch:
        with open('latest_branch.txt', 'w') as file:
            file.write(latest_branch)
        return latest_branch

    return None


async def check_updates(channel_ids):
    updated_channels = []
    for channel_id in channel_ids:
        # Get the latest videos from the YouTube channel
        response = requests.get(f'https://www.googleapis.com/youtube/v3/search?key={API_KEY}&channelId={channel_id}&part=snippet,id&order=date&maxResults=3')
        data = json.loads(response.text)

        # Check if 'items' key exists in data
        if 'items' in data and data['items']:
            new_videos = []
            for item in data['items']:
                video_id = item['id']['videoId']
                if os.path.exists(f'video_{video_id}.txt'):
                    # This video has been seen before
                    print(f'Video {video_id} has been seen before')
                    continue
                else:
                    # This is a new video
                    with open(f'video_{video_id}.txt', 'w') as file:
                        file.write(video_id)
                    new_videos.append(video_id)
            if new_videos:
                # Get the channel name
                response = requests.get(f'https://www.googleapis.com/youtube/v3/channels?key={API_KEY}&id={channel_id}&part=snippet')
                data = json.loads(response.text)
                channel_name = data['items'][0]['snippet']['title']
                updated_channels.append((channel_id, channel_name, new_videos))
    return updated_channels


def get_spotify_token():
    message = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    message_bytes = message.encode('ascii')
    base64_bytes = base64.b64encode(message_bytes)
    base64_message = base64_bytes.decode('ascii')

    headers = {
        'Authorization': f'Basic {base64_message}',
    }

    data = {
        'grant_type': 'client_credentials'
    }

    response = requests.post('https://accounts.spotify.com/api/token', headers=headers, data=data)
    return response.json()['access_token']


def get_followed_artists(token):
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get('https://api.spotify.com/v1/me/following?type=artist', headers=headers)
    response_data = response.json()
    if 'artists' in response_data:
        return [item['id'] for item in response_data['artists']['items']]
    else:
        print('Error getting followed artists:', response_data)
        return []


def check_new_releases(token, artist_ids):
    headers = {
        'Authorization': f'Bearer {token}',
    }

    new_releases = []
    for artist_id in artist_ids:
        response = requests.get(f'https://api.spotify.com/v1/artists/{artist_id}/albums', headers=headers)
        albums = response.json()['items']
        for album in albums:
            date_format = '%Y-%m-%d' if len(album['release_date']) > 4 else '%Y'
            release_date = datetime.datetime.strptime(album['release_date'], date_format).date()
            if release_date == datetime.date.today():
                new_releases.append((album['name'], album['artists'][0]['name']))

    return new_releases


def check_all_branches():
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    response = requests.get(f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/branches', headers=headers)
    data = response.json()
    return [branch['name'] for branch in data]


async def check_all_videos(channel_ids):
    all_videos = []
    user = await client.fetch_user('314618583923818496')
    for channel_id in channel_ids:
        try:
            response = requests.get(f'https://www.googleapis.com/youtube/v3/search?key={API_KEY}&channelId={channel_id}&part=id&order=date&maxResults=3')
            data = json.loads(response.text)
            if 'items' in data and data['items']:
                for item in data['items']:
                    video_id = item['id']['videoId']
                    all_videos.append(video_id)
        except Exception as e:
            await user.send(f'Error while checking videos for channel {channel_id}: {e}')

    return all_videos


def get_artist_top_tracks(token, artist_id):
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f'https://api.spotify.com/v1/artists/{artist_id}/top-tracks?country=US', headers=headers)
    response_data = response.json()
    if 'tracks' in response_data:
        return [track['name'] for track in response_data['tracks']]
    else:
        print('Error getting artist top tracks:', response_data)
        return []


async def background_check_updates():
    while True:
        user = await client.fetch_user('314618583923818496')

        updated_channels = await check_updates(channel_ids)
        for channel_id, channel_name, video_ids in updated_channels:
            for video_id in video_ids:
                video_url = f'https://www.youtube.com/watch?v={video_id}'
                await user.send(f'There is a new video on the YouTube channel {channel_name} (ID: {channel_id}).\n{video_url}')
        
        new_branch = check_new_branches()
        if new_branch:
            await user.send(f'There is a version of Godot!!!!!!!!\n\n\n\n\n\nNEW VERSION OF GODOT ALERT!!!')
        
        spotify_token = get_spotify_token()
        followed_artists = get_followed_artists(SPOTIFY_USER_TOKEN)
        new_releases = check_new_releases(spotify_token, followed_artists)
        for new_release in new_releases:
            album_name, artist_name = new_release
            await user.send(f'New release from {artist_name}: {album_name}')
        
        

        await asyncio.sleep(3600)


@client.event
async def on_ready():
    print(f'{client.user} is connected to Discord!')
    user = await client.fetch_user('314618583923818496')
    await user.send('Discord notifyer up!')
    
    await user.send('Testing YouTube')
    # Get a random video from a channel
    all_videos = await check_all_videos(channel_ids)
    await user.send('Got videos')
    if all_videos:
        video_id = random.choice(all_videos)
        await user.send('Chose random video')
        video_url = f'https://www.youtube.com/watch?v={video_id}'
        await user.send(f'Test message: Random video: {video_url}')
    else:
        await user.send('No videos found')

    await user.send('Testing Godot')
    # Get a random branch from Godot's GitHub
    all_branches = check_all_branches()
    await user.send('Got all branches')
    branch = random.choice(all_branches)
    await user.send(f'Test message: Random branch from Godot: {branch}')
    
    await user.send('Testing Spotify')
    # Get a random song from an artist you follow
    spotify_token = get_spotify_token()
    await user.send('Got spotify token')
    followed_artists = get_followed_artists(SPOTIFY_USER_TOKEN)
    await user.send('Got followed artists')
    random_artist = random.choice(followed_artists)
    await user.send('Got random artist')
    artist_top_tracks = get_artist_top_tracks(spotify_token, random_artist)
    await user.send('Got artist top tracks')

    while not artist_top_tracks and followed_artists:
        followed_artists.remove(random_artist)
        if followed_artists:
            random_artist = random.choice(followed_artists)
            artist_top_tracks = get_artist_top_tracks(spotify_token, random_artist)

    if artist_top_tracks:
        random_track = random.choice(artist_top_tracks)
        await user.send(f'Test message: Random track from a followed artist: {random_track}')
    else:
        await user.send('No top tracks found for any followed artists')

    client.loop.create_task(background_check_updates())


client.run(TOKEN)