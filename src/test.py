import requests
from bs4 import BeautifulSoup

def get_song_lyrics(song_title, artist_name, access_token):
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    search_url = 'https://api.genius.com/search'
    
    # Search for the song
    search_params = {
        'q': f'{song_title} {artist_name}'
    }
    search_response = requests.get(search_url, headers=headers, params=search_params)
    search_data = search_response.json()
    
    if search_data['response']['hits']:
        song_info = search_data['response']['hits'][0]['result']
        song_path = song_info['path']
        
        # Fetch the song page
        song_url = f'https://genius.com{song_path}'
        page_response = requests.get(song_url)
        
        # Parse the HTML to extract lyrics
        soup = BeautifulSoup(page_response.text, 'html.parser')
        lyrics_div = soup.find('div', class_='lyrics')
        if not lyrics_div:
            lyrics_div = soup.find('div', class_='Lyrics__Root-sc-1ynbvzw-0')
        
        if lyrics_div:
            lyrics = lyrics_div.get_text(strip=True)
            print(lyrics)
        else:
            print("Lyrics not found.")
    else:
        print("Song not found.")

# Replace these with your own details
song_title = 'Born To Die'
artist_name = 'Lana Del Rey'
access_token = '3-T1Z9F4ldaaMuQR4ArMFkvTN3a3GeUiuFv0FtF4QHhq-mQBQu4-gEumkqdC9Nqi'

get_song_lyrics(song_title, artist_name, access_token)
