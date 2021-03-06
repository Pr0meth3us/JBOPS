#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Description: Pull Playlists from Google Music and create Playlist in Plex
Author: Blacktwin
Requires: gmusicapi, plexapi, requests


 Example:

"""


from plexapi.server import PlexServer, CONFIG
from gmusicapi import Mobileclient

import requests
requests.packages.urllib3.disable_warnings()

PLEX_URL = ''
PLEX_TOKEN = ''
MUSIC_LIBRARY_NAME = 'Music'

## CODE BELOW ##

if not PLEX_URL:
    PLEX_URL = CONFIG.data['auth'].get('server_baseurl')
if not PLEX_TOKEN:
    PLEX_TOKEN = CONFIG.data['auth'].get('server_token')

# Connect to Plex Server
sess = requests.Session()
sess.verify = False
plex = PlexServer(PLEX_URL, PLEX_TOKEN, session=sess)

# Connect to Google Music, if not authorized prompt to authorize
# See https://unofficial-google-music-api.readthedocs.io/en/latest/reference/mobileclient.html
# for more information
mc = Mobileclient()
if not mc.oauth_login(device_id=Mobileclient.FROM_MAC_ADDRESS):
    mc.perform_oauth()


def round_down(num, divisor):
    """
    Parameters
    ----------
    num (int,str): Number to round down
    divisor (int): Rounding digit

    Returns
    -------
    Rounded down int
    """
    num = int(num)
    return num - (num%divisor)


def compare(ggmusic, pmusic):
    """
    Parameters
    ----------
    ggmusic (dict): Contains Playlist data from Google Music
    pmusic (object): Plex item found from search

    Returns
    -------
    pmusic (object): Matched Plex item
    """
    title = str(ggmusic['track']['title'].encode('ascii', 'ignore'))
    album = str(ggmusic['track']['album'].encode('ascii', 'ignore'))
    tracknum = int(ggmusic['track']['trackNumber'])
    duration = int(ggmusic['track']['durationMillis'])

    # Check if track numbers match
    if int(pmusic.index) == int(tracknum):
        return [pmusic]
    # If not track number, check track title and album title
    elif title == pmusic.title and (album == pmusic.parentTitle or
                                    album.startswith(pmusic.parentTitle)):
        return [pmusic]
    # Check if track duration match
    elif round_down(duration, 1000) == round_down(pmusic.duration, 1000):
        return [pmusic]
    # Lastly, check if title matches
    elif title == pmusic.title:
        return [pmusic]


def main():
    for pl in mc.get_all_user_playlist_contents():
        playlistName = pl['name']
        # Check for existing Plex Playlists, skip if exists
        if playlistName in [x.title for x in plex.playlists()]:
            print("Playlist: ({}) already available, skipping...".format(playlistName))
        else:
            playlistContent = []
            shareToken = pl['shareToken']
            # Go through tracks in Google Music Playlist
            for ggmusic in mc.get_shared_playlist_contents(shareToken):
                title = str(ggmusic['track']['title'].encode('ascii', 'ignore'))
                album = str(ggmusic['track']['album'].encode('ascii', 'ignore'))
                artist = str(ggmusic['track']['artist'])
                # Search Plex for Album title and Track title
                albumTrackSearch = plex.library.section(MUSIC_LIBRARY_NAME).searchTracks(
                        **{'album.title': album, 'track.title': title})
                # Check results
                if len(albumTrackSearch) == 1:
                    playlistContent += albumTrackSearch
                if len(albumTrackSearch) > 1:
                    for pmusic in albumTrackSearch:
                        albumTrackFound = compare(ggmusic, pmusic)
                        if albumTrackFound:
                            playlistContent += albumTrackFound
                            break
                # Nothing found from Album title and Track title
                if not albumTrackSearch or len(albumTrackSearch) == 0:
                    # Search Plex for Track title
                    trackSearch = plex.library.section(MUSIC_LIBRARY_NAME).searchTracks(
                            **{'track.title': title})
                    if len(trackSearch) == 1:
                        playlistContent += trackSearch
                    if len(trackSearch) > 1:
                        for pmusic in trackSearch:
                            trackFound = compare(ggmusic, pmusic)
                            if trackFound:
                                playlistContent += trackFound
                                break
                    # Nothing found from Track title
                    if not trackSearch or len(trackSearch) == 0:
                        # Search Plex for Artist
                        artistSearch = plex.library.section(MUSIC_LIBRARY_NAME).searchTracks(
                                **{'artist.title': artist})
                        for pmusic in artistSearch:
                            artistFound = compare(ggmusic, pmusic)
                            if artistFound:
                                playlistContent += artistFound
                                break
                        if not artistSearch or len(artistSearch) == 0:
                            print(u"Could not find in Plex:\n\t{} - {} {}".format(artist, album, title))
            print("Adding Playlist: {}".format(playlistName))
            plex.createPlaylist(playlistName, playlistContent)

main()
