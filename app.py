from flask import Flask, render_template, request, jsonify
import pickle
import pandas as pd
import requests
import os

app = Flask(__name__)

TMDB_API_KEY = "6c72dcf33d8559368a457d38228be17f"

def fetch_poster(movie_id):
    try:
        response = requests.get(
            f'https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US',
            timeout=5
        )
        data = response.json()
        poster_path = data.get('poster_path')
        if poster_path:
            return f"https://image.tmdb.org/t/p/w500{poster_path}"
    except Exception:
        pass
    return "https://via.placeholder.com/300x450?text=No+Poster"

def fetch_movie_details(movie_id):
    try:
        response = requests.get(
            f'https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US',
            timeout=5
        )
        data = response.json()
        return {
            'rating': round(data.get('vote_average', 0), 1),
            'year': data.get('release_date', '')[:4] if data.get('release_date') else 'N/A',
            'genres': [g['name'] for g in data.get('genres', [])[:2]],
            'overview': data.get('overview', '')[:120] + '...' if data.get('overview') else '',
            'poster': f"https://image.tmdb.org/t/p/w500{data['poster_path']}" if data.get('poster_path') else "https://via.placeholder.com/300x450?text=No+Poster"
        }
    except Exception:
        return {'rating': 'N/A', 'year': 'N/A', 'genres': [], 'overview': '', 'poster': 'https://via.placeholder.com/300x450?text=No+Poster'}

def recommend(movie, movies_df, similarity):
    movie_index = movies_df[movies_df['title'] == movie].index[0]
    distances = similarity[movie_index]
    recommended_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:11]

    results = []
    for i in recommended_list:
        movie_id = movies_df.iloc[i[0]].movie_id
        title = movies_df.iloc[i[0]].title
        details = fetch_movie_details(movie_id)
        results.append({
            'title': title,
            'movie_id': int(movie_id),
            **details
        })
    return results


movies_dict = None
movies_df = None
similarity = None

def load_data():
    global movies_dict, movies_df, similarity
    try:
        movies_dict = pickle.load(open('movie_dict.pkl', 'rb'))
        movies_df = pd.DataFrame(movies_dict)
        similarity = pickle.load(open('similarity.pkl', 'rb'))
        print("Data loaded successfully.")
    except FileNotFoundError as e:
        print(f"Warning: {e}. Using demo data.")
        movies_df = pd.DataFrame({
            'title': ['The Dark Knight', 'Inception', 'Interstellar', 'Parasite', 'Oppenheimer',
                      'Dune', 'The Batman', 'Avatar', 'Top Gun: Maverick', 'Everything Everywhere'],
            'movie_id': [155, 27205, 157336, 496243, 872585, 438631, 414906, 19995, 361743, 545611]
        })
        similarity = None

load_data()


@app.route('/')
def index():
    titles = movies_df['title'].sort_values().tolist() if movies_df is not None else []
    return render_template('index.html', movies=titles)

@app.route('/recommend', methods=['POST'])
def get_recommendations():
    data = request.get_json()
    movie = data.get('movie')
    if not movie or movies_df is None:
        return jsonify({'error': 'Invalid request'}), 400
    if similarity is None:
        return jsonify({'error': 'Similarity matrix not loaded. Please add similarity.pkl'}), 500
    try:
        results = recommend(movie, movies_df, similarity)
        return jsonify({'recommendations': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search')
def search():
    query = request.args.get('q', '').lower()
    if not query or movies_df is None:
        return jsonify([])
    matches = movies_df[movies_df['title'].str.lower().str.contains(query, na=False)]['title'].head(8).tolist()
    return jsonify(matches)

if __name__ == '__main__':
    app.run(debug=True, port=5000)