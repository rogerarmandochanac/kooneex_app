def get_headers():
    try:
        with open("token.txt", "r") as f:
            token = f.read().strip()
        return {"Authorization": f"Bearer {token}"}
    except:
        return {}

def save_headers(access_token):
    try:
        with open("token.txt", "w") as f:
            f.write(access_token)
        return {"Authorization": f"Bearer {access_token}"}
    except:
        return {}

