#!/usr/bin/python3

# see documentation at https://github.com/headrotor/masto-pinb

# pip3 install Mastodon.py
# https://mastodonpy.readthedocs.io/en/stable/
from mastodon import Mastodon

#pip3 install "pinboard>=2.0"
import pinboard

# https://github.com/Alir3z4/html2text
# pip3 install html2text
import html2text

# standard libraries
import time
import os.path
import re
import os
import argparse
import json

# options, might make these command-line

# False to keep Pinboard bookmarks private
pb_shared = False

# keep this many IDs in history cache file.
max_history = 120

# read authorization tokens from files.
# put '.secret' in .gitognore so you don't check in secrets to github 
masto_cred_file = 'masto_pinb_usercred.secret'
pinboard_cred_file = 'pinboard_auth.secret'

# number of previous toots to retrieve. Change this with the --get_last option
get_last = 20

parser = argparse.ArgumentParser(description='Arguments for Mastodon-Pinboard bookmarker app')

parser.add_argument('--toots', dest='toots', action='store_true', help="Bookmark user toots")

parser.add_argument('--log_json', dest='log_json', action='store_true', help="Log toots in JSON format to local file")

parser.add_argument('--favs', dest='favs', action='store_true', help="Bookmark user favorites")

parser.add_argument('--bmarks', dest='bmarks', action='store_true', help="Bookmark user Mastodon bookmarks")

parser.add_argument('--dry_run', dest='dry_run', action='store_true', help="Dry run: don't actually bookmark anything")

parser.add_argument('--verbose', dest='verbose', action='store_true', help="Print actions as they occur")

parser.add_argument('--get_last', dest='get_last',  type=int, help=f"retrieve only last GET_LAST toots (default={get_last})")

args = parser.parse_args()

#modes: select which kinds of toots to bookmark
modes = []
if args.toots:
    modes.append('toots')
if args.favs:
    modes.append('favs')
if args.bmarks:
    modes.append('bmarks')

if args.get_last is not None:
    get_last = args.get_last
#no modes specified, default to all of them
if len(modes) == 0:
    modes = ['toots', 'favs', 'bmarks']

print(modes)
    
# first change to code directory so auth file is local 
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# load API token for Pinboard
try:
    with open(pinboard_cred_file) as pbfile:
        pinboard_API_token = pbfile.read()
        pinboard_API_token = pinboard_API_token.strip()
except FileNotFoundError:
    # read authorization tokens from files.
    print(f"can't find pinboard credential file '{pinboard_cred_file}'")
    print("Get API token from https://pinboard.in/settings/password")
    exit()

# test for existence of Mastodon API credential file    
if not os.path.isfile(masto_cred_file):
    print(f"Can't find Mastodon user credential file '{masto_cred_file}'")
    print(f"To register this app, see https://mastodonpy.readthedocs.io/en/stable")
    exit()

# Instantiate API class instances we will use throughout
    
# if we exceed rate limit, just quit and try again next time.

mastodon = Mastodon(access_token=masto_cred_file,
                    ratelimit_method='throw')

if args.verbose:
    print(f"Mastodon rate limit remaining: {mastodon.ratelimit_remaining}")

pb = pinboard.Pinboard(pinboard_API_token)

h2t = html2text.HTML2Text()
h2t.ignore_links = False

# for each mode (favorites, user toots, bookmarks) get each toot and bookmark it
for mode in modes:
    print(f"processing {mode}")

    # cache ids of bookmarked toots in these files to help
    # prevent duplicate bookmarks the next time we run this
    # (Pinboard is OK with that but let's not anyway ;)
    cache_file_name = f"cached_{mode}_ids.secret" 
    
    # read list of already-bookmarked toot IDs from file
    try:
        with open(cache_file_name) as cache_file:
            cached_ids = cache_file.read().split("\n")
            # remove newlines
            cached_ids = [bid.strip() for bid in cached_ids]

    except FileNotFoundError:
        # read authorization tokens from files.
        print("Don't see saved favorite IDs, skipping")
        cached_ids = []

    ####################################################################
    # Read list of toots for this mode
    ####################################################################

    if mode == 'favs':
        toots = mastodon.favourites(limit=get_last)
    elif mode == 'bmarks':
        toots = mastodon.bookmarks(limit=get_last)
    elif mode == 'toots':
        user = mastodon.me()
        toots = mastodon.account_statuses(user['id'],
                                          only_media=False,
                                          pinned=False,
                                          exclude_replies=False,
                                          exclude_reblogs=True,
                                          tagged=None,
                                          limit=get_last)
        
    # sort toots by ID so they are in quasi-temporal order
    toots = sorted(toots, key=lambda f: int(f['id']))

    bookmarked_count = 0
    for  toot in toots:

        this_id = str(toot['id'])
        if args.verbose:
            print(f"testing {mode} toot {this_id}")
        if this_id not in cached_ids:
            if args.verbose:
                print(f"Bookmarking toot {this_id}")

            # if we are archiving toots, save data to file in JSON format
            if args.log_json:
                with open(f'{mode}.json', 'a') as jsonfile:
                    json.dump(toot, jsonfile, default=str)
                    # so we can look at it in a text editor
                    jsonfile.write("\n")

            # make short description
            if mode == 'favs':
                short_desc = f"Fav toot from {toot['account']['username']}"
            elif mode == 'toots':
                short_desc = f"Toot from {toot['account']['username']}"
            elif mode == 'bmarks':
                short_desc = f"Bookmarked toot from {toot['account']['username']}"

            # get extended description
            ext_desc = h2t.handle(toot['content'])

            # URL of this toot
            url = toot['url']
            
            # add mastodon ID to description for debug 
            ext_desc += f"mast-id:{toot['id']}"    
            if args.verbose:
                print(ext_desc)

            if not args.dry_run:
                status = pb.posts.add(url=url,
                                      description=short_desc,
                                      extended=ext_desc,
                                      tags=[f"masto-{mode}"],
                                      shared=pb_shared)

                if status:
                    cached_ids.append(this_id)
                    bookmarked_count += 1
            else:
                print(f"Dry run bookmarking {mode} id {this_id}")

    # write back list of bookmarked IDs to cache file
    if bookmarked_count > 0:
        if args.verbose:
            print(f"{bookmarked_count} {mode} bookmarks saved to Pinboard")
        # sort and remove duplicate ids:
        cached_ids = sorted(set(cached_ids))
        if len(cached_ids) > max_history:
            #cache only most recently bookmarked IDs
            cached_ids = cached_ids[-max_history:]
        with open(cache_file_name, "w") as idfile:
            idfile.write("\n".join(cached_ids) + "\n")

    print("done!")
exit()
