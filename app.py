import requests
import random
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

TMDB_API_KEY = "8e4b382195543a2d0155cec668ba1d11"
TMDB_BASE_URL = "https://api.themoviedb.org/3"

GENRE_MAP = {
    "akcja": 28,
    "przygoda": 12,
    "animacja": 16,
    "komedia": 35,
    "kryminal": 80,
    "dokument": 99,
    "dramat": 18,
    "familijny": 10751,
    "fantasy": 14,
    "horror": 27,
    "tajemnica": 9648,
    "romans": 10749,
    "sci-fi": 878,
    "thriller": 53,
    "wojenny": 10752
}

def format_movie(item):
    poster = f"https://image.tmdb.org/t/p/w500{item['poster_path']}" if item.get("poster_path") else None
    backdrop = f"https://image.tmdb.org/t/p/w780{item['backdrop_path']}" if item.get("backdrop_path") else poster
    return {
        "id": item["id"],
        "tytul": item.get("title") or item.get("name"),
        "rok": (item.get("release_date") or "b.d.")[:4],
        "ocena": f"{item.get('vote_average', 0):.1f}",
        "opis": item.get("overview") or "Brak opisu w języku polskim.",
        "plakat": poster,
        "tlo": backdrop
    }

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/filmy")
def get_filmy():
    gatunek = request.args.get("gatunek", "wszystkie")
    szukaj = request.args.get("szukaj", "").strip()
    page = request.args.get("page", 1, type=int)

    if szukaj:
        url = f"{TMDB_BASE_URL}/search/movie?api_key={TMDB_API_KEY}&language=pl-PL&query={szukaj}&page={page}"
    else:
        genre_id = GENRE_MAP.get(gatunek)
        genre_param = f"&with_genres={genre_id}" if genre_id else ""
        url = f"{TMDB_BASE_URL}/discover/movie?api_key={TMDB_API_KEY}&language=pl-PL&sort_by=popularity.desc{genre_param}&page={page}"

    try:
        response = requests.get(url, timeout=5)
        data = response.json()
    except Exception:
        return jsonify({"results": [], "total_pages": 0})

    filmy_list = [format_movie(item) for item in data.get("results", []) if item.get("poster_path")]

    return jsonify({
        "results": filmy_list,
        "total_pages": data.get("total_pages", 1)
    })

@app.route("/api/rekomendacje")
def get_rekomendacje():
    # Pobieranie kolekcji filmów pod specjalne sekcje tematyczne
    sections = {
        "breaking_bad": f"{TMDB_BASE_URL}/discover/movie?api_key={TMDB_API_KEY}&language=pl-PL&with_genres=80,18,53&sort_by=vote_count.desc&page=1",
        "scifi_classics": f"{TMDB_BASE_URL}/discover/movie?api_key={TMDB_API_KEY}&language=pl-PL&with_genres=878&sort_by=vote_average.desc&vote_count.gte=3000&page=1",
        "action_hits": f"{TMDB_BASE_URL}/discover/movie?api_key={TMDB_API_KEY}&language=pl-PL&with_genres=28&sort_by=popularity.desc&page=1"
    }
    
    result = {}
    for key, url in sections.items():
        try:
            res = requests.get(url, timeout=5).json()
            result[key] = [format_movie(item) for item in res.get("results", [])[:10] if item.get("poster_path")]
        except Exception:
            result[key] = []

    return jsonify(result)

@app.route("/api/losowy")
def get_losowy_film():
    page = random.randint(1, 10)
    url = f"{TMDB_BASE_URL}/discover/movie?api_key={TMDB_API_KEY}&language=pl-PL&sort_by=popularity.desc&page={page}"
    try:
        res = requests.get(url, timeout=5).json()
        results = res.get("results", [])
        if results:
            selected = random.choice(results)
            return jsonify({"id": selected["id"]})
    except Exception:
        pass
    return jsonify({"error": "Nie udało się wylosować filmów"}), 500

@app.route("/api/film/<int:movie_id>")
def get_film_details(movie_id):
    details_url = f"{TMDB_BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&language=pl-PL&append_to_response=videos,credits,images"
    
    try:
        res = requests.get(details_url, timeout=5).json()
    except Exception:
        return jsonify({"error": "Błąd pobierania danych"}), 500

    trailer_key = None
    videos = res.get("videos", {}).get("results", [])
    for vid in videos:
        if vid.get("site") == "YouTube" and vid.get("type") == "Trailer":
            trailer_key = vid.get("key")
            break
    if not trailer_key and videos:
        trailer_key = videos[0].get("key")

    cast_members = [m["name"] for m in res.get("credits", {}).get("cast", [])[:6]]

    # Pobieranie kadrów / zdjęć z filmu
    images = []
    backdrops = res.get("images", {}).get("backdrops", [])[:6]
    for img in backdrops:
        images.append(f"https://image.tmdb.org/t/p/w780{img['file_path']}")

    return jsonify({
        "id": res.get("id"),
        "tytul": res.get("title"),
        "rok": (res.get("release_date") or "b.d.")[:4],
        "ocena": f"{res.get('vote_average', 0):.1f}",
        "opis": res.get("overview") or "Brak opisu dla tego filmu.",
        "obsada": ", ".join(cast_members) if cast_members else "Brak danych o obsadzie",
        "zdjecia": images,
        "trailer_key": trailer_key
    })

if __name__ == "__main__":
    app.run(debug=True)
