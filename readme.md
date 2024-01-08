# Use [Google Photos Toolkit](https://github.com/xob0t/Google-Photos-Toolkit) instead

A few scripts to help you delete all media from your google photos that is taking up storage in your account.

Dependencies:
```
pip install google-auth google-auth-oauthlib google-api-python-client undetected-chromedriver selenium-wire rich

```
## 1. photos_db_update.py
Uses official api to create a db with all your media uploaded to google photos

credentials.json - https://developers.google.com/photos/library/guides/get-started#enable-the-api

## 2. chrome_google_login.py
Starts chromedriver for you to log into google.
Google photo's media info panel must be opened for the next script to work.

## 3. delete_with_chrome.py
For every media file in the db, opens a URL in chrome and checks if it takes up space or not.
Deletes the media if it is, otherwise skips it. Marks in in the db accordingly.
