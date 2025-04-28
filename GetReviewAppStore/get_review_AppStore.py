aimport jwt
import time
import requests
from flask import Flask, jsonify

app = Flask(__name__)
def generate_jwt(issuer_id, key_id, private_key):
    try:
        header = {
            "alg": "ES256",
            "typ": "JWT",
            "kid": key_id
        }
        payload = {
            "iss": issuer_id,
            "aud": "appstoreconnect-v1",
            "iat": int(time.time()),
            "exp": int(time.time() + 20 * 60)  # 20 minutes timestamp
        }
        with open(private_key, 'r') as file:
            key_data = file.read()
        token = jwt.encode(headers=header, payload=payload, key=key_data, algorithm="ES256")
        return token
    except Exception as e:
        print(f"Error generating JWT: {e}")
        return ""


def get_reviews(url, headers):
    all_reviews = []

    while url:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            reviews = data.get('data', [])
            extracted_reviews = [{'title': review['attributes']['title'],
                                  'body': review['attributes']['body']} for review in reviews]
            all_reviews.extend(extracted_reviews)

            # Check if there is a next page
            url = data.get('links', {}).get('next')
        else:
            print(f"Error fetching reviews: {response.status_code}")
            return []

    return all_reviews

@app.route('/get_review', methods=['GET'])
def get_review():
    p8 = "AuthKey_B835BY2YLK.p8"  # Path to your .p8 private key file
    kid = "B835BY2YLK"  # Your Key ID
    iss = "8c15e2d9-9dbf-4036-a7ee-d78fbfb62bab"  # Your Issuer ID
    token = generate_jwt(iss, kid, p8)

    # API URL to fetch reviews (initial request)
    url = "https://api.appstoreconnect.apple.com/v1/apps/1618915911/customerReviews?limit=200"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    # Execute the original script
    result = get_reviews(url, headers)
    # Return the result as JSON
    return jsonify(result)
if __name__ == '__main__':
    # Run the app on host 0.0.0.0 and port 5000
    app.run(host='0.0.0.0', port=5002)
