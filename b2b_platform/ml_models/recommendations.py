# ml_models/recommendations.py

import os
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.neighbors import NearestNeighbors
import joblib

from django.core.exceptions import ObjectDoesNotExist

# This function needs to be called from a Django context to access models
def train_and_save_knn_model():
    """
    Extracts order data, trains an item-to-item KNN model,
    and saves the model and necessary mappings to disk.
    """
    # We must import Django models here, inside the function,
    # because this script is outside the standard Django app structure.
    from accounts.models import Order, Product

    print("Starting model training process...")

    # 1. Data Extraction & Transformation
    # Get all orders with a positive status
    orders = Order.objects.filter(status__in=['paid', 'completed', 'shipped']).values('buyer_id', 'product_id')
    
    if not orders:
        print("No sufficient order data to train the model. Exiting.")
        return

    df = pd.DataFrame(list(orders))
    
    # We'll use a simple interaction score of 1 for any order
    df['interaction_score'] = 1
    
    # Drop duplicates in case a user ordered the same product multiple times
    df = df.drop_duplicates(subset=['buyer_id', 'product_id'])

    print(f"Loaded {len(df)} unique user-product interactions.")

    # 2. Build the Utility Matrix
    # Create pivot table
    user_item_matrix = df.pivot(index='buyer_id', columns='product_id', values='interaction_score').fillna(0)
    
    # Create mappings from product_id to matrix column index and vice-versa
    product_id_to_idx = {product_id: i for i, product_id in enumerate(user_item_matrix.columns)}
    idx_to_product_id = {i: product_id for product_id, i in product_id_to_idx.items()}

    # Convert to a sparse matrix for efficiency
    sparse_user_item_matrix = csr_matrix(user_item_matrix.values)

    # 3. Train the KNN Model
    # We fit the model on the transpose of the matrix to learn item-item similarity
    # (items are rows, users are columns)
    item_user_matrix = sparse_user_item_matrix.T
    
    model_knn = NearestNeighbors(metric='cosine', algorithm='brute', n_neighbors=10)
    model_knn.fit(item_user_matrix)
    print("KNN model trained successfully.")

    # 4. Save the Model and Mappings
    # Ensure the directory to save the models exists
    model_dir = 'ml_models/saved_models/'
    os.makedirs(model_dir, exist_ok=True)
    
    model_path = os.path.join(model_dir, 'knn_model.joblib')
    map_path = os.path.join(model_dir, 'product_mappings.joblib')

    joblib.dump(model_knn, model_path)
    joblib.dump({'id_to_idx': product_id_to_idx, 'idx_to_id': idx_to_product_id}, map_path)

    print(f"Model saved to {model_path}")
    print(f"Mappings saved to {map_path}")
    print("Training process complete.")

# Note: We will create the recommendation function in a later step.
# This file is now ready for Phase 2.

def get_recommendations(user, num_recs=4):
    """
    Loads the trained KNN model and generates product recommendations for a given user.
    """
    from accounts.models import Order, Product

    model_dir = 'ml_models/saved_models/'
    model_path = os.path.join(model_dir, 'knn_model.joblib')
    map_path = os.path.join(model_dir, 'product_mappings.joblib')

    # Check if the model files exist before trying to load them
    if not os.path.exists(model_path) or not os.path.exists(map_path):
        print("Model files not found. Please train the model first.")
        return []

    # Load the saved model and mappings
    model_knn = joblib.load(model_path)
    mappings = joblib.load(map_path)
    product_id_to_idx = mappings['id_to_idx']
    idx_to_product_id = mappings['idx_to_id']

    try:
        # Find the most recent product the user has ordered
        latest_order = Order.objects.filter(buyer=user, status__in=['paid', 'completed', 'shipped']).latest('created_at')
        seed_product_id = latest_order.product.id
        
        # Check if the product the user ordered is in our model's vocabulary
        if seed_product_id not in product_id_to_idx:
            print(f"Seed product {seed_product_id} not in model training data. Cannot provide recommendations.")
            return []

        # Get the internal index of our seed product
        seed_product_idx = product_id_to_idx[seed_product_id]

        # Use the model to find the nearest neighbors (num_recs + 1 because it includes the product itself)
        distances, indices = model_knn.kneighbors([model_knn._fit_X[seed_product_idx]], n_neighbors=num_recs + 1)
        
        # The indices are returned as a 2D array, so we get the first row
        similar_product_indices = indices.flatten()
        
        # Get the actual product IDs from the indices
        recommended_ids = []
        for idx in similar_product_indices:
            # Skip the first item, as it's the seed product itself
            if idx != seed_product_idx:
                recommended_ids.append(idx_to_product_id[idx])
        
        # Get the products the user has already ordered to filter them out
        already_ordered_ids = set(Order.objects.filter(buyer=user).values_list('product_id', flat=True))
        
        # Fetch the recommended products from the database, excluding already ordered ones
        final_recommendations = list(Product.objects.filter(id__in=recommended_ids).exclude(id__in=already_ordered_ids)[:num_recs])

        return final_recommendations

    except ObjectDoesNotExist:
        # This happens if the user has no past orders
        print(f"User {user.id} has no past orders to base recommendations on.")
        return []
    except Exception as e:
        print(f"An error occurred during recommendation generation: {e}")
        return []