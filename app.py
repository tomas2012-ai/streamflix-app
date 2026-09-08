import os
import requests
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# Klucz i adres API TMDB (wbudowany domyślny klucz publiczny dla aplikacji demonstracyjnych)
TMDB_API_KEY = "c9856d0cb57c3f14bf75bdc6c06bca5f" # lub Twój własny klucz TMDB
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/movies')
def get_movies():
    try:
        # Pobieramy kilka stron popularnych filmów z TMDB, aby była potężna baza (ok. 60-100 filmów)
        movies = []
        for page in range(1, 4):
            url = f"{TMDB_BASE_URL}/movie/popular?api_key={TMDB_API_KEY}&language=pl-PL&page={page}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                for item in data.get('results', []):
                    poster_path = item.get('poster_path')
                    poster_url = f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else "https://images.unsplash.com/photo-1485846234645-a62644f84728?q=80&w=600"
                    
                    movies.append({
                        "id": item.get('id'),
                        "title": item.get('title'),
                        "genre": "Film kinowy", # TMDB zwraca ID gatunków, upraszczamy dla płynności
                        "rating": round(item.get('vote_average', 0.0), 1),
                        "poster": poster_url,
                        "description": item.get('overview') or "Brak opisu dla tej produkcji."
                    })
        return jsonify(movies)
    except Exception as e:
        print("Błąd pobierania z TMDB:", e)
        return jsonify([])

@app.route('/api/trailer/<int:movie_id>')
def get_trailer(movie_id):
    try:
        url = f"{TMDB_BASE_URL}/movie/{movie_id}/videos?api_key={TMDB_API_KEY}&language=pl-PL"
        response = requests.get(url)
        data = response.json()
        results = data.get('results', [])
        
        # Szukamy zwiastuna na YouTube
        trailer_key = None
        for vid in results:
            if vid.get('site') == 'YouTube' and vid.get('type') == 'Trailer':
                trailer_key = vid.get('key')
                break
        
        # Jeśli nie ma po polsku, szukamy angielskiego
        if not trailer_key:
            url_en = f"{TMDB_BASE_URL}/movie/{movie_id}/videos?api_key={TMDB_API_KEY}&language=en-US"
            resp_en = requests.get(url_en)
            for vid in resp_en.json().get('results', []):
                if vid.get('site') == 'YouTube' and vid.get('type') == 'Trailer':
                    trailer_key = vid.get('key')
                    break
        
        # Domyślny zwiastun zastępczy w razie braku
        embed_url = f"https://www.youtube-nocookie.com/embed/{trailer_key}" if trailer_key else "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"
        return jsonify({"trailer": embed_url})
    except Exception:
        return jsonify({"trailer": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"})

if __name__ == '__main__':
    app.run(debug=True)
