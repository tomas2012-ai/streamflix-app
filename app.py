import requests
import random
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

TMDB_API_KEY = "8e4b382195543a2d0155cec668ba1d11"
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# Gatunki dla filmów
MOVIE_GENRE_MAP = {
    "akcja": 28, "przygoda": 12, "animacja": 16, "komedia": 35, 
    "kryminal": 80, "dokument": 99, "dramat": 18, "familijny": 10751, 
    "fantasy": 14, "horror": 27, "tajemnica": 9648, "romans": 10749, 
    "sci-fi": 878, "thriller": 53, "wojenny": 10752
}

# Gatunki dla seriali (w TMDB niektóre są połączone, np. Akcja i Przygoda)
TV_GENRE_MAP = {
    "akcja": 10759, "przygoda": 10759, "animacja": 16, "komedia": 35, 
    "kryminal": 80, "dokument": 99, "dramat": 18, "familijny": 10762, 
    "fantasy": 10765, "tajemnica": 9648, "romans": 10749, 
    "sci-fi": 10765, "wojenny": 10768
}

def format_media(item, typ="movie"):
    poster = f"https://image.tmdb.org/t/p/w500{item['poster_path']}" if item.get("poster_path") else None
    backdrop = f"https://image.tmdb.org/t/p/w780{item['backdrop_path']}" if item.get("backdrop_path") else poster
    
    # Filmy mają 'title' i 'release_date', seriale mają 'name' i 'first_air_date'
    tytul = item.get("title") or item.get("name")
    data_premiery = item.get("release_date") or item.get("first_air_date") or "b.d."
    
    # Wykrywamy typ na podstawie dostępnych pól, jeśli nie został podany twardo
    wykryty_typ = "tv" if "first_air_date" in item else "movie"

    return {
        "id": item["id"],
        "tytul": tytul,
        "rok": data_premiery[:4] if data_premiery != "b.d." else "b.d.",
        "ocena": f"{item.get('vote_average', 0):.1f}",
        "opis": item.get("overview") or "Brak opisu w języku polskim.",
        "plakat": poster,
        "tlo": backdrop,
        "typ": wykryty_typ # Wysyłamy informację na frontend, czy to film czy serial
    }

@app.route("/")
def home():
    return render_template("index.html")

# Zmieniłem ścieżkę z /api/filmy na /api/katalog (ale na froncie możesz to dostosować)
@app.route("/api/katalog")
def get_katalog():
    gatunek = request.args.get("gatunek", "wszystkie")
    szukaj = request.args.get("szukaj", "").strip()
    page = request.args.get("page", 1, type=int)
    typ = request.args.get("typ", "movie") # 'movie' dla filmów, 'tv' dla seriali

    # Wybieramy odpowiednią mapę gatunków
    genre_map = TV_GENRE_MAP if typ == "tv" else MOVIE_GENRE_MAP

    if szukaj:
        url = f"{TMDB_BASE_URL}/search/{typ}?api_key={TMDB_API_KEY}&language=pl-PL&query={szukaj}&page={page}"
    else:
        genre_id = genre_map.get(gatunek)
        genre_param = f"&with_genres={genre_id}" if genre_id else ""
        url = f"{TMDB_BASE_URL}/discover/{typ}?api_key={TMDB_API_KEY}&language=pl-PL&sort_by=popularity.desc{genre_param}&page={page}"

    try:
        response = requests.get(url, timeout=5)
        data = response.json()
    except Exception:
        return jsonify({"results": [], "total_pages": 0})

    katalog_list = [format_media(item, typ) for item in data.get("results", []) if item.get("poster_path")]

    return jsonify({
        "results": katalog_list,
        "total_pages": data.get("total_pages", 1)
    })

@app.route("/api/rekomendacje")
def get_rekomendacje():
    # Dodaliśmy dedykowane sekcje z serialami!
    sections = {
        "popular_series": f"{TMDB_BASE_URL}/discover/tv?api_key={TMDB_API_KEY}&language=pl-PL&sort_by=popularity.desc&page=1",
        "breaking_bad": f"{TMDB_BASE_URL}/discover/tv?api_key={TMDB_API_KEY}&language=pl-PL&with_genres=80,18&sort_by=vote_count.desc&page=1",
        "scifi_classics": f"{TMDB_BASE_URL}/discover/movie?api_key={TMDB_API_KEY}&language=pl-PL&with_genres=878&sort_by=vote_average.desc&vote_count.gte=3000&page=1",
        "action_hits": f"{TMDB_BASE_URL}/discover/movie?api_key={TMDB_API_KEY}&language=pl-PL&with_genres=28&sort_by=popularity.desc&page=1"
    }
    
    result = {}
    for key, url in sections.items():
        try:
            res = requests.get(url, timeout=5).json()
            result[key] = [format_media(item) for item in res.get("results", [])[:10] if item.get("poster_path")]
        except Exception:
            result[key] = []

    return jsonify(result)

@app.route("/api/losowy")
def get_losowy():
    typ = request.args.get("typ", "movie") # Pozwala wylosować film albo serial
    page = random.randint(1, 10)
    url = f"{TMDB_BASE_URL}/discover/{typ}?api_key={TMDB_API_KEY}&language=pl-PL&sort_by=popularity.desc&page={page}"
    try:
        res = requests.get(url, timeout=5).json()
        results = res.get("results", [])
        if results:
            selected = random.choice(results)
            return jsonify({"id": selected["id"], "typ": typ})
    except Exception:
        pass
    return jsonify({"error": "Nie udało się wylosować"}), 500

# Zmiana: teraz musimy podać 'typ' (movie lub tv), żeby TMDB wiedziało gdzie szukać szczegółów
@app.route("/api/detale/<typ>/<int:item_id>")
def get_details(typ, item_id):
    if typ not in ["movie", "tv"]:
        return jsonify({"error": "Nieprawidłowy typ treści"}), 400

    details_url = f"{TMDB_BASE_URL}/{typ}/{item_id}?api_key={TMDB_API_KEY}&language=pl-PL&append_to_response=videos,credits,images"
    
    try:
        res = requests.get(details_url, timeout=5).json()
    except Exception:
        return jsonify({"error": "Błąd pobierania danych"}), 500

    # Szukanie zwiastuna
    trailer_key = None
    videos = res.get("videos", {}).get("results", [])
    for vid in videos:
        if vid.get("site") == "YouTube" and vid.get("type") == "Trailer":
            trailer_key = vid.get("key")
            break
    if not trailer_key and videos:
        trailer_key = videos[0].get("key")

    cast_members = [m["name"] for m in res.get("credits", {}).get("cast", [])[:6]]

    # Pobieranie kadrów
    images = []
    backdrops = res.get("images", {}).get("backdrops", [])[:6]
    for img in backdrops:
        images.append(f"https://image.tmdb.org/t/p/w780{img['file_path']}")

    # Pola nazywają się inaczej dla filmów i seriali
    tytul = res.get("title") or res.get("name")
    data_premiery = res.get("release_date") or res.get("first_air_date") or "b.d."

    return jsonify({
        "id": res.get("id"),
        "typ": typ,
        "tytul": tytul,
        "rok": data_premiery[:4] if data_premiery != "b.d." else "b.d.",
        "ocena": f"{res.get('vote_average', 0):.1f}",
        "opis": res.get("overview") or "Brak opisu dla tego tytułu.",
        "obsada": ", ".join(cast_members) if cast_members else "Brak danych o obsadzie",
        "zdjecia": images,
        "trailer_key": trailer_key,
        "liczba_sezonow": res.get("number_of_seasons") # Nowość: przydatne dla seriali
    })

if __name__ == "__main__":
    app.run(debug=True)