# pip3 install Mastodon.py
# Only need to run this once to generate
# Mastodon authorization token files.
# https://mastodonpy.readthedocs.io/en/stable/

# P.S. Don't check this into git with your actual credentials!

from mastodon import Mastodon

Mastodon.create_app(
    'masto_pinb',
    api_base_url = 'https://mastodon.social',
    to_file = 'masto_pinb_clientcred.secret'
)

mastodon = Mastodon(client_id = 'masto_pinb_clientcred.secret',)
mastodon.log_in(
    'MASTODON_USERID',
    'MASTODON_PASSW',
    to_file = 'masto_pinb_usercred.secret'
)

