import json

import httpx

from .oauth import access_token


def send_kakao(settings, integration, title, body, link):
    if settings.provider_mode == "test":
        return "test-kakao"
    if settings.provider_mode != "live":
        raise ValueError("카카오 연결 설정이 필요합니다")
    token = access_token(settings, integration)
    template = {
        "object_type": "text",
        "text": (title + "\n" + body)[:900],
        "link": {"web_url": link, "mobile_web_url": link},
        "button_title": "회의록 확인",
    }
    with httpx.Client(timeout=30) as client:
        response = client.post(
            "https://kapi.kakao.com/v2/api/talk/memo/default/send",
            headers={"Authorization": f"Bearer {token}"},
            data={"template_object": json.dumps(template, ensure_ascii=False)},
        )
    response.raise_for_status()
    if response.json().get("result_code") != 0:
        raise ValueError("카카오 접수 실패")
    return "kakao-accepted"
