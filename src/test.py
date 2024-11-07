import requests

def get_lyrics(artist, title):
    # Format the API URL with the artist and song title
    url = f"https://api.lyrics.ovh/v1/{artist}/{title}"
    
    try:
        # Make the API call
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        
        # Parse the JSON response to get the lyrics
        data = response.json()
        lyrics = data.get("lyrics", "Lyrics not found.")
        
        print(f"Lyrics for '{title}' by {artist}:\n")
        print(lyrics)
        
    except requests.exceptions.HTTPError as err:
        print(f"Error: {err}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage
artist = "Adele"
title = "Hello"
get_lyrics(artist, title)
