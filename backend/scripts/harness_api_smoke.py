from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app


def main() -> None:
    client = TestClient(app)
    client.__enter__()
    try:
        health = client.get("/api/health")
        print(f"health={health.status_code}")
        health.raise_for_status()
        assert health.json()["code"] == 0

        login = client.post("/api/auth/login", json={"username": "2021000001", "password": "guangdong11"})
        print(f"login={login.status_code}")
        login.raise_for_status()
        token = login.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        me = client.get("/api/auth/me", headers=headers)
        print(f"me={me.status_code}")
        me.raise_for_status()

        academic = client.get("/api/student/2021000001/academic-info", headers=headers)
        print(f"academic={academic.status_code}")
        academic.raise_for_status()

        progress = client.get("/api/student/2021000001/graduation-progress", headers=headers)
        print(f"progress={progress.status_code}")
        progress.raise_for_status()

        chat = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "query": "graduation progress summary",
                "student_id": "2021000001",
                "major_name": "电子科学与技术",
                "inputs": {"student_id": "2021000001", "major_name": "电子科学与技术"},
            },
        )
        print(f"ai_chat={chat.status_code}")
        chat.raise_for_status()
        print(f"ai_conversation_id={chat.json()['data']['conversation_id']}")

        schedule = client.get("/api/schedule", params={"term": "2025-2026-1", "week": 7}, headers=headers)
        print(f"schedule={schedule.status_code}")
        schedule.raise_for_status()
        assert len(schedule.json()["data"]["courses"]) > 0
        schedule_id = schedule.json()["data"]["courses"][0]["id"]

        note = client.patch(f"/api/schedule/{schedule_id}/note", headers=headers, json={"note": "smoke note"})
        print(f"schedule_note={note.status_code}")
        note.raise_for_status()

        sync = client.post("/api/time-plan/sync-from-schedule", params={"term": "2025-2026-1"}, headers=headers)
        print(f"time_plan_sync={sync.status_code}")
        sync.raise_for_status()

        events = client.get("/api/time-plan/events", headers=headers)
        print(f"time_plan_events={events.status_code}")
        events.raise_for_status()
        assert len(events.json()["data"]) > 0

        topics = client.get("/api/forum/topics", headers=headers)
        print(f"forum_topics={topics.status_code}")
        topics.raise_for_status()
        assert len(topics.json()["data"]) > 0
        topic_id = topics.json()["data"][0]["id"]

        like1 = client.post(f"/api/forum/topics/{topic_id}/like", headers=headers)
        like2 = client.post(f"/api/forum/topics/{topic_id}/like", headers=headers)
        print(f"forum_like={like1.status_code}/{like2.status_code}")
        like1.raise_for_status()
        like2.raise_for_status()
        assert like1.json()["data"]["likes"] == like2.json()["data"]["likes"]

        upload = client.post(
            f"/api/forum/topics/{topic_id}/files",
            headers=headers,
            files={"file": ("smoke.txt", b"forum attachment smoke", "text/plain")},
        )
        print(f"forum_upload={upload.status_code}")
        upload.raise_for_status()
        file_id = upload.json()["data"]["id"]

        download = client.get(f"/api/forum/files/{file_id}/download", headers=headers)
        print(f"forum_download={download.status_code}")
        download.raise_for_status()
        assert download.content == b"forum attachment smoke"

        comment = client.post(
            f"/api/forum/topics/{topic_id}/comments",
            headers=headers,
            json={"content": "smoke comment with attachment"},
        )
        print(f"forum_comment={comment.status_code}")
        comment.raise_for_status()
        comment_id = comment.json()["data"]["id"]

        comment_upload = client.post(
            f"/api/forum/topics/{topic_id}/comments/{comment_id}/files",
            headers=headers,
            files={"file": ("comment-smoke.txt", b"comment attachment smoke", "text/plain")},
        )
        print(f"forum_comment_upload={comment_upload.status_code}")
        comment_upload.raise_for_status()
        comment_file_id = comment_upload.json()["data"]["id"]

        comment_download = client.get(f"/api/forum/files/{comment_file_id}/download", headers=headers)
        print(f"forum_comment_download={comment_download.status_code}")
        comment_download.raise_for_status()
        assert comment_download.content == b"comment attachment smoke"

        error_case = client.post(
            "/api/ai/error-cases",
            headers=headers,
            json={
                "question": "graduation question",
                "wrong_answer": "wrong answer",
                "expected_answer": "expected answer",
                "reason": "smoke test",
            },
        )
        print(f"error_case={error_case.status_code}")
        error_case.raise_for_status()
        assert error_case.json()["data"]["status"] == "pending"

        error_cases = client.get("/api/ai/error-cases", headers=headers)
        print(f"error_cases={error_cases.status_code}")
        error_cases.raise_for_status()
        assert len(error_cases.json()["data"]) > 0
    finally:
        client.__exit__(None, None, None)


if __name__ == "__main__":
    main()
