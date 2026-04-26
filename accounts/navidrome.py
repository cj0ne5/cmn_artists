import logging
import uuid
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


def create_navidrome_user(base_url: str, admin_user: str, admin_pass: str,
                          username: str, display_name: str, email: str, password: str) -> None:
    """
    Log in to Navidrome as admin and create a new user. Raises on failure.
    """
    session = requests.Session()
    resp = session.post(base_url.rstrip("/") + "/auth/login",
                        json={"username": admin_user, "password": admin_pass})
    resp.raise_for_status()
    data = resp.json()
    token = data.get("token")
    if not token:
        raise RuntimeError(f"Navidrome login response missing token: {data}")

    client_id = str(uuid.uuid4())
    try:
        domain = urlparse(base_url).hostname
        session.cookies.set("X-ND-Client-Unique-Id", client_id,
                            domain=domain if domain else None, path="/")
    except Exception:
        session.cookies.set("X-ND-Client-Unique-Id", client_id, path="/")

    session.headers.update({
        "Authorization": f"Bearer {token}",
        "x-nd-authorization": f"Bearer {token}",
        "x-nd-client-unique-id": client_id,
        "Accept": "application/json",
    })

    resp = session.post(
        base_url.rstrip("/") + "/api/user",
        json={
            "userName": username,
            "name": display_name,
            "email": email,
            "password": password,
            "isAdmin": False,
        },
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()
