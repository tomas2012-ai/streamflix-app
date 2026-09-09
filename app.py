from flask import Flask, render_template, request, jsonify
import requests
import random
import os

app = Flask(__name__)

# ==============================================================================
# KONFIGURACJA I KLUCZ API TMDB
# Wklej swój klucz API pobrany z https://www.themoviedb.org/settings/api
# ==============================================================================
TMDB_API_KEY = "8e4b382195543a2d0155cec668ba1d11"
BASE_URL = "https://api.themoviedb.org/3"

# Słownik identyfikatorów gatunków w TMDB
GENRES = {
    'movie': {
        'akcja': 28, 'przygoda': 12, 'animacja': 16, 'komedia': 35,
        'kryminal': 80, 'dokument': 99, 'dramat': 18, 'familijny': 10751,
        'fantasy': 14, 'historia': 36, 'horror': 27, 'muzyczny': 10402,
        'tajemnica': 9648, 'romans': 10749, 'sci-fi': 878, 'thriller': 53,
        'wojenny': 10752, 'western': 37
    },
    'tv': {
        'akcja': 10759, 'animacja': 16, 'komedia': 35, 'kryminal': 80,
        'dokument': 99, 'dramat': 18, 'familijny': 10751, 'tajemnica': 9648,
        'news': 10763, 'reality': 10764, 'sci-fi': 10765, 'soap': 10766,
        'talk': 10767, 'wojna': 10768, 'western': 37
    }
}

# Najpopularniejsi dostawcy VOD w Polsce (ID w systemie TMDB)
PROVIDERS_PL = {
    'netflix': {'id': '8', 'name': 'Netflix', 'color': '#E50914'},
    'disney': {'id': '337', 'name': 'Disney+', 'color': '#0063E5'},
    'max': {'id': '1194', 'name': 'Max', 'color': '#002BE7'},
    'prime': {'id': '119', 'name': 'Amazon Prime Video', 'color': '#00A8E1'},
    'canal': {'id': '564', 'name': 'Canal+ Online', 'color': '#000000'},
    'apple': {'id': '350', 'name': 'Apple TV+', 'color': '#333333'},
    'skyshowtime': {'id': '1773', 'name': 'SkyShowtime', 'color': '#0099FF'},
    'player': {'id': '531', 'name': 'Player', 'color': '#FF0055'},
    'polsat': {'id': '1782', 'name': 'Polsat Box Go', 'color': '#FF8800'}
}

def check_api_key():
    """Pomocnicza funkcja sprawdzająca czy klucz API został uzupełniony."""
    return TMDB_API_KEY and TMDB_API_KEY != "WPROWADZ_SWOJ_KLUCZ_API_TUTAJ"

@app.route('/')
def index():
    """Główny widok strony."""
    return render_template('index.html')

@app.route('/api/katalog')
def api_katalog():
    """
    Główny endpoint katalogu: obsługa wyszukiwania, filtrowania po gatunkach,
    dostawcach VOD (Polska), sortowania oraz paginacji.
    """
    if not check_api_key():
        return jsonify({
            "total_pages": 1,
            "results": [],
            "error": "Brak poprawnego klucza TMDB API w pliku app.py!"
        }), 400

    typ = request.args.get('typ', 'movie')  # 'movie' lub 'tv'
    page = request.args.get('page', 1, type=int)
    gatunek = request.args.get('gatunek', 'wszystkie')
    provider = request.args.get('provider', 'wszystkie')
    szukaj = request.args.get('szukaj', '').strip()
    sort_by = request.args.get('sort', 'popularity.desc')
    min_rating = request.args.get('min_rating', 0, type=float)

    params = {
        "api_key": TMDB_API_KEY,
        "language": "pl-PL",
        "page": page
    }

    # JEŚLI UŻYTKOWNIK WYSZUKUJE SŁOWO KLUCZOWE
    if szukaj:
        url = f"{BASE_URL}/search/{typ}"
        params['query'] = szukaj
        params['include_adult'] = 'false'
    else:
        # PRZEGLĄDANIE KATALOGU Z FILTRAMI
        url = f"{BASE_URL}/discover/{typ}"
        params['sort_by'] = sort_by
        params['vote_count.gte'] = 10  # Odrzucamy pozycje bez ocen

        if min_rating > 0:
            params['vote_average.gte'] = min_rating

        # Filtrowanie po gatunku
        if gatunek != 'wszystkie' and gatunek in GENRES.get(typ, {}):
            params['with_genres'] = GENRES[typ][gatunek]

        # Filtrowanie po platformie VOD w regionie Polski (PL)
        if provider != 'wszystkie':
            params['with_watch_providers'] = provider
            params['watch_region'] = 'PL'

    try:
        response = requests.get(url, params=params, timeout=8)
        if response.status_code != 200:
            return jsonify({"total_pages": 1, "results": [], "error": f"Błąd API: {response.status_code}"})

        data = response.json()
        results = []

        for item in data.get('results', []):
            tytul = item.get('title') if typ == 'movie' else item.get('name')
            org_tytul = item.get('original_title') if typ == 'movie' else item.get('original_name')
            data_premiery = item.get('release_date') if typ == 'movie' else item.get('first_air_date')
            rok = data_premiery[:4] if data_premiery else "Brak"

            poster_path = item.get('poster_path')
            backdrop_path = item.get('backdrop_path')

            results.append({
                'id': item.get('id'),
                'typ': typ,
                'tytul': tytul or org_tytul or "Bez tytułu",
                'original_title': org_tytul,
                'rok': rok,
                'ocena': round(item.get('vote_average', 0), 1),
                'glosy': item.get('vote_count', 0),
                'opis': item.get('overview') or 'Brak opisu w języku polskim.',
                'plakat': f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "https://via.placeholder.com/500x750/131318/FFFFFF?text=Brak+Okładki",
                'tlo': f"https://image.tmdb.org/t/p/original{backdrop_path}" if backdrop_path else "",
                'popularity': item.get('popularity', 0)
            })

        total_pages = min(data.get('total_pages', 1), 500)
        return jsonify({"total_pages": total_pages, "results": results, "page": page})

    except requests.exceptions.RequestException as e:
        return jsonify({"total_pages": 1, "results": [], "error": str(e)}), 500


@app.route('/api/trending')
def api_trending():
    """Pobiera najgorętsze pozycje tego tygodnia (Trending)."""
    if not check_api_key():
        return jsonify([])

    url = f"{BASE_URL}/trending/all/week"
    params = {"api_key": TMDB_API_KEY, "language": "pl-PL"}

    try:
        res = requests.get(url, params=params, timeout=8).json()
        results = []
        for item in res.get('results', [])[:12]:
            typ = item.get('media_type', 'movie')
            if typ not in ['movie', 'tv']:
                continue
            tytul = item.get('title') if typ == 'movie' else item.get('name')
            data_prem = item.get('release_date') if typ == 'movie' else item.get('first_air_date')
            results.append({
                'id': item.get('id'),
                'typ': typ,
                'tytul': tytul,
                'rok': data_prem[:4] if data_prem else "",
                'ocena': round(item.get('vote_average', 0), 1),
                'plakat': f"https://image.tmdb.org/t/p/w500{item['poster_path']}" if item.get('poster_path') else "",
                'tlo': f"https://image.tmdb.org/t/p/original{item['backdrop_path']}" if item.get('backdrop_path') else ""
            })
        return jsonify(results)
    except Exception:
        return jsonify([])


@app.route('/api/detale/<typ>/<id>')
def api_detale(typ, id):
    """Pobiera pełne, szczegółowe dane filmu/serialu wraz z obsadą, dostawcami VOD i zwiastunem."""
    if not check_api_key():
        return jsonify({"error": "Brak klucza API"}), 400

    params = {
        "api_key": TMDB_API_KEY,
        "language": "pl-PL",
        "append_to_response": "credits,videos,watch/providers,similar"
    }

    try:
        response = requests.get(f"{BASE_URL}/{typ}/{id}", params=params, timeout=8)
        if response.status_code != 200:
            return jsonify({"error": "Nie znaleziono pozycji"}), 404

        data = response.json()

        tytul = data.get('title') if typ == 'movie' else data.get('name')
        data_premiery = data.get('release_date') if typ == 'movie' else data.get('first_air_date')
        czas_trwania = f"{data.get('runtime')} min" if typ == 'movie' and data.get('runtime') else ""
        if typ == 'tv':
            sezony = data.get('number_of_seasons', 1)
            odcinki = data.get('number_of_episodes', 0)
            czas_trwania = f"{sezony} sez. ({odcinki} odc.)"

        # Szukanie zwiastuna w serwisie YouTube
        trailer_key = ""
        videos = data.get('videos', {}).get('results', [])
        for v in videos:
            if v.get('site') == 'YouTube' and v.get('type') in ['Trailer', 'Teaser']:
                trailer_key = v.get('key')
                if v.get('type') == 'Trailer':  # Priorytet dla oficjalnego zwiastuna
                    break

        # Obsada (Aktorzy)
        cast = []
        for member in data.get('credits', {}).get('cast', [])[:10]:
            cast.append({
                'name': member.get('name'),
                'character': member.get('character'),
                'photo': f"https://image.tmdb.org/t/p/w185{member['profile_path']}" if member.get('profile_path') else None
            })

        # Dostawcy VOD w Polsce (Flatrate - abonament)
        providers_list = []
        pl_providers = data.get('watch/providers', {}).get('results', {}).get('PL', {}).get('flatrate', [])
        for prov in pl_providers:
            providers_list.append({
                'name': prov.get('provider_name'),
                'logo': f"https://image.tmdb.org/t/p/w92{prov['logo_path']}" if prov.get('logo_path') else ""
            })

        # Gatunki jako tekst
        genres_names = [g['name'] for g in data.get('genres', [])]

        # Podobne pozycje
        similar = []
        for sim in data.get('similar', {}).get('results', [])[:6]:
            sim_tytul = sim.get('title') if typ == 'movie' else sim.get('name')
            similar.append({
                'id': sim.get('id'),
                'typ': typ,
                'tytul': sim_tytul,
                'ocena': round(sim.get('vote_average', 0), 1),
                'plakat': f"https://image.tmdb.org/t/p/w342{sim['poster_path']}" if sim.get('poster_path') else ""
            })

        return jsonify({
            "id": data.get('id'),
            "typ": typ,
            "tytul": tytul,
            "tagline": data.get('tagline', ''),
            "rok": data_premiery[:4] if data_premiery else "Brak",
            "ocena": round(data.get('vote_average', 0), 1),
            "glosy": data.get('vote_count', 0),
            "opis": data.get('overview') or 'Brak polskiego opisu dla tego tytułu.',
            "czas_trwania": czas_trwania,
            "gatunki": genres_names,
            "plakat": f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get('poster_path') else "",
            "tlo": f"https://image.tmdb.org/t/p/original{data.get('backdrop_path')}" if data.get('backdrop_path') else "",
            "trailer_key": trailer_key,
            "cast": cast,
            "providers": providers_list,
            "similar": similar
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/losowy')
def api_losowy():
    """Losuje losowy popularny film lub serial na podstawie wybranych filtrów."""
    if not check_api_key():
        return jsonify({"error": "Brak klucza API"}), 400

    typ = request.args.get('typ', 'movie')
    gatunek = request.args.get('gatunek', 'wszystkie')
    
    random_page = random.randint(1, 10)
    params = {
        "api_key": TMDB_API_KEY,
        "language": "pl-PL",
        "page": random_page,
        "vote_count.gte": 50
    }

    if gatunek != 'wszystkie' and gatunek in GENRES.get(typ, {}):
        params['with_genres'] = GENRES[typ][gatunek]

    try:
        res = requests.get(f"{BASE_URL}/discover/{typ}", params=params, timeout=8).json()
        results = res.get('results', [])
        if results:
            item = random.choice(results)
            return jsonify({"id": item['id'], "typ": typ})
        return jsonify({"error": "Brak wyników"}), 44
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/providers')
def api_providers():
    """Zwraca listę obsługiwanych platform VOD wraz z ich kolorami i nazwą."""
    return jsonify(PROVIDERS_PL)


if __name__ == '__main__':
    print("=" * 60)
    print(" 🚀 StreamVibe Ultra Server Uruchomiony!")
    print(" 🌐 Otwórz w przeglądarce: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, port=5000)