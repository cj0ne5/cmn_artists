import logging
import uuid
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


def _admin_session(base_url: str, admin_user: str, admin_pass: str):
    """Authenticate as admin and return (session, token)."""
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
    return session


def create_navidrome_user(base_url: str, admin_user: str, admin_pass: str,
                          username: str, display_name: str, email: str, password: str) -> str:
    """
    Log in to Navidrome as admin and create a new user.
    Returns the Navidrome user ID. Raises on failure.
    """
    session = _admin_session(base_url, admin_user, admin_pass)
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
    print("new navidrome user created- their id is " + resp.json()["id"])
    return resp.json()["id"]


def update_navidrome_password(base_url: str, admin_user: str, admin_pass: str,
                              nd_user_id: str, new_password: str) -> None:
    """Update a Navidrome user's password via the admin API."""
    session = _admin_session(base_url, admin_user, admin_pass)
    resp = session.put(
        base_url.rstrip("/") + f"/api/user/{nd_user_id}",
        json={"password": new_password},
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()


def grant_library_access(base_url: str, admin_user: str, admin_pass: str,
                         nd_user_id: str, library_id: str, sample_library_id: str = None) -> None:
    """Grant a Navidrome user access to the given library, keeping the sample library too."""
    library_ids = [library_id]
    if sample_library_id is not None:
        library_ids.append(sample_library_id)
    session = _admin_session(base_url, admin_user, admin_pass)
    resp = session.put(
        base_url.rstrip("/") + f"/api/user/{nd_user_id}/library",
        json={"libraryIds": library_ids},
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()


def revoke_library_access(base_url: str, admin_user: str, admin_pass: str,
                          nd_user_id: str, sample_library_id: str = None) -> None:
    """Remove paid library access for a Navidrome user, keeping the sample library."""
    library_ids = [sample_library_id] if sample_library_id is not None else []
    session = _admin_session(base_url, admin_user, admin_pass)
    resp = session.put(
        base_url.rstrip("/") + f"/api/user/{nd_user_id}/library",
        json={"libraryIds": library_ids},
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()
