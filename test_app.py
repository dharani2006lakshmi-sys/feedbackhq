import os
import tempfile

with tempfile.TemporaryDirectory() as tmp:
    os.environ["FEEDBACK_DB"] = os.path.join(tmp, "test.db")
    import app as feedback_app

    feedback_app.init_db()
    client = feedback_app.app.test_client()

    # Separate login portals render cleanly
    assert b"user@feedbackhq.com" in client.get("/login").data
    assert b"admin@feedbackhq.com" in client.get("/admin/login").data
    assert client.get("/dashboard").status_code == 302

    # Cross-portal enforcement: admin cannot sign in on user portal
    r = client.post(
        "/login",
        data={"email": "admin@feedbackhq.com", "password": "admin1234"},
        follow_redirects=True,
    )
    assert b"Admin Login" in r.data

    # Cross-portal enforcement: user cannot sign in on admin portal
    r = client.post(
        "/admin/login",
        data={"email": "user@feedbackhq.com", "password": "user1234"},
        follow_redirects=True,
    )
    assert b"User Login" in r.data

    # Register a new user and verify user-only flow
    r = client.post(
        "/register",
        data={"username": "alice", "email": "alice@example.com", "password": "Password1!"},
        follow_redirects=True,
    )
    assert r.status_code == 200 and b"Account created" in r.data

    r = client.post(
        "/login",
        data={"email": "alice@example.com", "password": "Password1!"},
        follow_redirects=True,
    )
    assert r.status_code == 200 and b"Submit" in r.data
    # Regular user blocked from admin dashboard
    assert b"Admin access required" in client.get("/dashboard", follow_redirects=True).data

    # Regular user submits feedback and sees only their own item on /feedback
    r = client.post(
        "/submit",
        data={"product": "Alice Widget", "rating": "5", "comment": "Works great", "date": "2026-11-11"},
        follow_redirects=True,
    )
    assert b"Alice Widget" in r.data
    assert b"Checkout Flow" not in r.data
    client.get("/logout")

    # Admin login accesses /dashboard and sees all feedback
    r = client.post(
        "/admin/login",
        data={"email": "admin@feedbackhq.com", "password": "admin1234"},
        follow_redirects=True,
    )
    assert r.status_code == 200 and b"Total Feedback" in r.data
    all_fb = client.get("/feedback")
    assert b"Alice Widget" in all_fb.data and b"Checkout Flow" in all_fb.data
    assert client.get("/static/style.css").status_code == 200
    assert client.get("/static/main.js").status_code == 200
    assert client.get("/logout", follow_redirects=True).status_code == 200
    print("All FeedbackHQ role-separation checks passed.")
