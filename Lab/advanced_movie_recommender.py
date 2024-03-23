print("\n===== Advanced AI Movie Recommender System =====\n")
import pandas as pd
import re
from scipy.sparse import vstack
from sklearn.metrics.pairwise import cosine_similarity

# And then to load it again when necessary
from joblib import load

print("Loading models and data...")
kmeans = load('./save/kmeans_movie_clusters.pkl')
tfidf_vectorizer = load('./save/tfidf_vectorizer.pkl')
movie_df_with_tags = pd.read_csv('./save/movie_df_with_tags.csv') 
# Fit and transform the metadata to TF-IDF features
print("Fitting and transforming metadata to TF-IDF features...\n")
tfidf_matrix = tfidf_vectorizer.fit_transform(movie_df_with_tags['metadata'])

def enter_favorite_movies():
    user_favorites_titles = []
    print("Enter your favorite movies (press enter to finish):")
    while True:
        title_input = input()
        if title_input == "":
            break
        user_favorites_titles.append(title_input)
    return user_favorites_titles if user_favorites_titles else -1

def get_user_preferences():
    # Prompt for a rating and convert to float
    rating_input = input("Enter your minimum rating (as a float, [0-5], e.g., 3.5): ")
    try:
        rating = float(rating_input)
    except ValueError:
        print("Invalid rating. Setting to default 3.5.")
        rating = 3.5
    
    # Prompt for keywords and split into a list
    keywords_input = input("Enter your keywords separated by commas (e.g., space, sci-fi): ")
    keywords = [keyword.strip() for keyword in keywords_input.split(',')] if keywords_input else []
    
    return rating, keywords

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

def get_content_based_recommendations(movie_df_with_tags, favorite_movie_titles, tfidf_matrix, num_recommendations=10, min_rating=0, keywords=None):
    # Assuming get_movie_indices is defined elsewhere and correctly returns indices of favorite movies
    favorite_movie_indices = get_movie_indices(favorite_movie_titles)
    if not favorite_movie_indices:
        return "No favorite movies found in the dataset."
    
    # Generate user profile from favorite movies
    # This section was problematic to get working and eventually I had to resort to asking ChatGPT to solve it,
    # that also needed a couple of rounds. The issue was that the sparse matrix was not being converted to a dense array,
    # and thus not accepted by the cosine_similarity function.
    user_profile = vstack([tfidf_matrix[index] for index in favorite_movie_indices]).mean(axis=0)
    user_profile_dense = user_profile.A 

    # Compute cosine similarities between user profile and all movies
    cosine_similarities = cosine_similarity(user_profile_dense, tfidf_matrix).flatten()

    # Create a series with the similarities scores, index matching the movie DataFrame
    similarities_series = pd.Series(cosine_similarities, index=movie_df_with_tags.index)

    # Sort the movies based on similarity score, in descending order
    sorted_similarities = similarities_series.sort_values(ascending=False)

    recommended_movie_indices = []
    for idx in sorted_similarities.index:
        # Skip the favorite movies
        if idx in favorite_movie_indices:
            continue
        
        # Check the movie rating. This was inserted towards the end of this endeavour, to also include collaboration based filtering.
        movie_rating = movie_df_with_tags.at[idx, 'rating']
        movie_metadata = movie_df_with_tags.at[idx, 'metadata']
        
        # Check the movie rating
        if movie_rating >= min_rating:
            # Check if keywords are specified and if metadata contains any of the keywords
            if keywords:
                # Ensure keywords is a list for proper iteration, even if it's a single keyword
                if isinstance(keywords, str):
                    keywords = [keywords]
                keyword_match = any(str(keyword).lower() in str(movie_metadata).lower() for keyword in keywords)
            else:
                # If no keywords specified, consider it a match
                keyword_match = True
            
            if keyword_match:
                recommended_movie_indices.append(idx)
                if len(recommended_movie_indices) == num_recommendations:
                    break

    # Get the movie titles for the recommended indices
    recommended_movie_titles = movie_df_with_tags.loc[recommended_movie_indices, 'title'].tolist()
    return recommended_movie_titles

while True:
    favorite_movie_titles = enter_favorite_movies()
    if favorite_movie_titles == -1:
        print("No favorite movies entered. Exiting...")
        exit()
    print(f"Movies entered: {', '.join(favorite_movie_titles)}\n")

    rating, keywords = get_user_preferences()
    print(f"Rating {rating}" + f"and containing any of the keywords:\n{', '.join(keywords)}" if keywords else "")

    favorite_movie_indices = get_movie_indices(favorite_movie_titles)

    # Getting 10 movie recommendations from the content-based approach
    recommended_titles = get_content_based_recommendations(movie_df_with_tags, favorite_movie_titles, tfidf_matrix, 5, min_rating=rating, keywords=keywords)

    # Getting 5 movie recommendations from the cluster-based approach excluding those recommended by the content-based approach
    # With the min_rating set to a voluntary number, to also include some collaborative filtering
    kmeans_recommended_titles = recommend_movies_based_on_clusters(movie_df_with_tags, favorite_movie_indices,
                                                                    num_recommendations=5, movies_to_exclude=recommended_titles, min_rating=rating, keywords=keywords)


    print("Recommended movies based on your favorites:")
    print(f"\nMost similar movies with an average rating of at least {rating}" + f" and containing any of the keywords:\n{', '.join(keywords)}" if keywords else "")
    print("===========================================================")
    for title in recommended_titles:
        print(title)

    if kmeans_recommended_titles == "No recommendations found.":
        print("\nNo recommendations found using K-Means based on the search criteria. Consider lowering the minimum rating or use more keywords.")
    else:
        print("\nSimilar but not that similar:")
        print("=============================")
        for title in kmeans_recommended_titles:
            print(title)

    print("\nWould you like to get more recommendations? (yes/no)")
    more_recommendations = input()
    if more_recommendations.lower() != 'yes':
        break