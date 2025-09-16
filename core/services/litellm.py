import json
import http.client

from pydantic import BaseModel
from core.settings import settings


class Team(BaseModel):
    team_alias: str
    team_id: str


class Key(BaseModel):
    key: str


base_url = settings.model_dump().get("requrv_hive_endpoint") or ""
hive_master_key = settings.model_dump().get("requrv_master_key") or ""


def create_team(team_alias: str, admin_id: str) -> Team:
    try:
        conn = http.client.HTTPSConnection(base_url)
        payload = json.dumps(
            {
                "team_alias": team_alias,
                "members_with_roles": [{"role": "admin", "user_id": f"{admin_id}"}],
            }
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {hive_master_key}",
        }
        conn.request("POST", "/team/new", payload, headers)
        res = conn.getresponse()
        data = res.read()
        json_data = json.loads(data.decode("utf-8"))
    except Exception as e:
        raise e

    return Team.model_validate(json_data, strict=False)


def create_key(team_id: str) -> Key:
    try:
        conn = http.client.HTTPSConnection(base_url)
        payload = json.dumps({"team_id": team_id, "send_invite_email": False})
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {hive_master_key}",
        }
        conn.request("POST", "/key/generate", payload, headers)
        res = conn.getresponse()
        data = res.read()
        json_data = json.loads(data.decode("utf-8"))
    except Exception as e:
        raise e
    
    return Key.model_validate(json_data, strict=False)
