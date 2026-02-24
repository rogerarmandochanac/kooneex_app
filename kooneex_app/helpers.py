from kivy.app import App

def get_headers():
    app = App.get_running_app()
    token = getattr(app, "token", None)

    if not token:
        return {}

    return {
        "Authorization": f"Bearer {token}"
    }

