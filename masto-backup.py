#!/usr/bin/python3

# see documentation at https://github.com/headrotor/masto-pinb

# pip3 install Mastodon.py
# https://mastodonpy.readthedocs.io/en/stable/
from mastodon import Mastodon

# standard libraries
import time
import os
import argparse
import json
from datetime import datetime

# read authorization tokens from files.
# put '.secret' in .gitognore so you don't check in secrets to github 
masto_cred_file = 'masto_pinb_usercred.secret'

# wait this many seconds between page requests
wait_seconds = 1.0

# get this many pages (zero means onlt get first page)
get_npages = 0

# number of previous toots to retrieve. Change this with the --get_last option
get_last = 40

parser = argparse.ArgumentParser(description='Arguments for Mastodon backup app')

parser.add_argument('--toots', dest='toots', action='store_true', help="Bookmark user toots")

parser.add_argument('--favs', dest='favs', action='store_true', help="Bookmark user favorites")

parser.add_argument('--bmarks', dest='bmarks', action='store_true', help="Bookmark user Mastodon bookmarks")

parser.add_argument('--verbose', dest='verbose', action='store_true', help="Print actions as they occur")

parser.add_argument('--all_pages', dest='all_pages', action='store_true', help="Tries to get all pages available. May take some time!")

parser.add_argument('--get_last', dest='get_last',  type=int, help=f"retrieve only GET_LAST toots per page (default={get_last})")

parser.add_argument('--get_n_pages', dest='get_npages',  type=int, help=f"retrieve N_PAGES pages (default = 1). Ignored with --all_pages ")

parser.add_argument('--page_wait', dest='page_wait', type=float, help=f"wait WAIT_SECONDS between page requests to stay inside API limits (default= {wait_seconds}")

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
    
if args.page_wait is not None:
    wait_seconds = args.page_wait

if args.get_npages is not None:
    get_npages = args.get_npages
    
#no modes specified, default to all of them
if len(modes) == 0:
    modes = ['toots', 'favs', 'bmarks']

# first change to code directory so auth file is local 
os.chdir(os.path.dirname(os.path.abspath(__file__)))


# test for existence of Mastodon API credential file    
if not os.path.isfile(masto_cred_file):
    print(f"Can't find Mastodon user credential file '{masto_cred_file}'")
    print(f"To register this app, see https://mastodonpy.readthedocs.io/en/stable")
    exit()

# Instantiate API class instances we will use throughout
# Try to pace requests under rate limit, otherwise wait
mastodon = Mastodon(access_token=masto_cred_file,
                    ratelimit_method='pace')


# for each mode (favorites, user toots, bookmarks) get each toot and archive it
for mode in modes:

    if args.verbose:
        print(f"Processing {mode}: rate limit remaining: {mastodon.ratelimit_remaining}")
    
    iso_now = datetime.now().isoformat()
    # split date portion from time and milliseconds
    iso_split = iso_now.split("T")
    json_filename = f"{mode}-backup{iso_split[0]}.json"

    # create file we will append to
    jsonfile = open(json_filename, 'w')
        
    ####################################################################
    # Read list of toots for this mode
    ####################################################################

    if mode == 'favs':
        page = mastodon.favourites(limit=get_last)
    elif mode == 'bmarks':
        page = mastodon.bookmarks(limit=get_last)
    elif mode == 'toots':
        user = mastodon.me()
        page = mastodon.account_statuses(user['id'],
                                          only_media=False,
                                          pinned=False,
                                          exclude_replies=False,
                                          exclude_reblogs=True,
                                          tagged=None,
                                          limit=get_last)

    archived_count = 0
    page_count = 0

    while ((page_count < get_npages) or (args.all_pages)):

        # get next page
        if page_count > 0: 
            if args.verbose:
                print(f"Fetching next page {page_count}")
            time.sleep(wait_seconds) 
            page = mastodon.fetch_next(page)
            
        if page is None:
            if args.verbose:
                print("no more pages to fetch")
            break
            

        # save a page of toots by appending to json file
        # sort in reverse so latest toots are first
        reverse_toots = sorted(page, key=lambda f: -int(f['id']))
        for  toot in reverse_toots:

            archived_count += 1
            this_id = str(toot['id'])
            if args.verbose:
                print(f"archiving to json {mode} id {this_id}")


            # if we are logging toots, save data to file in JSON format
            # Here's where we could get any media associated with toot and
            # archive it as well
            json.dump(toot, jsonfile, default=str)
            # so we can look at it in a text editor
            jsonfile.write("\n")
        page_count += 1
                    
    # only cache first (most recent) pages of results
    if args.verbose:
        print(f"{archived_count} posts appended to {json_filename}")
    jsonfile.close()
