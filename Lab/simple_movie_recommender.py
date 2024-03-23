import pandas as pd
import re

# And then to load it again when necessary
from joblib import load
kmeans = load('./save/kmeans_movie_clusters.pkl')
movie_df_with_tags = pd.read_csv('./save/movie_df_with_tags_clustered.csv') 

def enter_favorite_movies():
    user_favorites_titles = []
    print("Enter your favorite movies (press enter to finish):")
    while True:
        title_input = input()
        if title_input == "":
            break
        user_favorites_titles.append(title_input)
    return user_favorites_titles

def get_movie_indices(favorite_movie_titles):
    favorite_movie_indices = []
    for title in favorite_movie_titles:
        # Matches whole words (regex \b) to exclude some potential non-intended matches
        matched_indices = movie_df_with_tags.index[movie_df_with_tags['title'].str.contains(r'\b' + re.escape(title) + r'\b', case=False, regex=True)]
        if not matched_indices.empty:
            # Further narrowing it down by only taking the first match if there are multiple matches
            # This would then make it possible for it to recommend other movies in e.g. a trilogy.
            favorite_movie_indices.append(matched_indices[0])
        else:
            print(f"Warning: '{title}' not found in the movie database.")
    return favorite_movie_indices

def recommend_movies_based_on_clusters(movie_df_with_tags, favorite_movie_indices, num_recommendations=10, movies_to_exclude=[], min_rating=0, keywords=[]):
    # Find the clusters for the favorite movies
    favorite_clusters = movie_df_with_tags.iloc[favorite_movie_indices]['cluster'].unique()
    
    # Filter movies that are in the same clusters
    recommended_movies = movie_df_with_tags[movie_df_with_tags['cluster'].isin(favorite_clusters)]
    
    # Exclude the favorite movies from the recommendations
    recommendations = recommended_movies[~recommended_movies.index.isin(favorite_movie_indices)]

    # Also exlude movies specified in movies_to_exclude if specified
    if movies_to_exclude:
        recommendations = recommendations[~recommendations['title'].isin(movies_to_exclude)]

    # Exclude movies with a rating below min_rating if specified
    if min_rating > 0:
        recommendations = recommendations[recommendations['rating'] >= min_rating]
    
    # Exclude movies that do not contain the keywords, if specified
    if keywords:
        recommendations = recommendations[recommendations['metadata'].str.contains('|'.join(keywords), case=False, na=False)]
    
    # Randomly pick 'num_recommendations' movies, unless there are not enough movies
    recommendations = recommendations.sample(n=num_recommendations if len(recommendations) > num_recommendations else len(recommendations))
    
    if recommendations.empty:
        return "No recommendations found."

    return recommendations['title'].tolist()

favorite_movie_titles = enter_favorite_movies()
favorite_movie_indices = get_movie_indices(favorite_movie_titles)
recommended_titles = recommend_movies_based_on_clusters(movie_df_with_tags, favorite_movie_indices)

print("\nRecommended movies based on your favorites:")
print("===========================================")
for title in recommended_titles:
    print(title)