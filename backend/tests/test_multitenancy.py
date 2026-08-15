from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.application.auth.service import create_access_token
from app.core.config import get_settings
from app.domain.business.models import Customer, Department, Employee, Product, ProductCategory, SalesOrder, SalesOrderItem
from app.domain.users.models import Organization, User
from app.infrastructure.database import Base, get_db
from app.main import app


@pytest.fixture()
def tenant_app(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    get_settings().storage_root = str(tmp_path / "storage")

    def override_db():
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with TestingSession() as db:
        tokens, organizations = {}, {}
        for suffix, revenue in (("a", Decimal("100.00")), ("b", Decimal("900.00"))):
            org = Organization(name=f"Organization {suffix.upper()}")
            db.add(org); db.flush()
            user = User(organization_id=org.id, email=f"owner-{suffix}@example.com", full_name=f"Owner {suffix.upper()}", password_hash="unused", role="owner")
            category = ProductCategory(organization_id=org.id, name=f"Category-{suffix}")
            department = Department(organization_id=org.id, code=f"D-{suffix}", name=f"Department {suffix}")
            customer = Customer(organization_id=org.id, customer_number=f"C-{suffix}", company_name=f"Customer {suffix}", industry="Technology", email=f"customer-{suffix}@example.com", country="India", region=f"Region {suffix}")
            db.add_all([user, category, department, customer]); db.flush()
            employee = Employee(organization_id=org.id, employee_number=f"E-{suffix}", department_id=department.id, first_name="Sales", last_name=suffix, email=f"employee-{suffix}@example.com", job_title="Manager", hire_date=date(2025, 1, 1), salary=Decimal("1000"))
            product = Product(organization_id=org.id, sku=f"SKU-{suffix}", category_id=category.id, name=f"Product {suffix}", unit_cost=Decimal("10"), unit_price=revenue, reorder_level=1)
            db.add_all([employee, product]); db.flush()
            order = SalesOrder(organization_id=org.id, order_number=f"ORDER-{suffix}", customer_id=customer.id, sales_rep_id=employee.id, order_date=date(2026, 8, 1), status="completed", currency="USD")
            db.add(order); db.flush()
            db.add(SalesOrderItem(organization_id=org.id, sales_order_id=order.id, product_id=product.id, quantity=1, unit_price=revenue, discount_amount=0))
            db.flush()
            tokens[suffix] = create_access_token(db, user)
            organizations[suffix] = org.id
        viewer = User(organization_id=organizations["a"], email="viewer-a@example.com", full_name="Viewer A", password_hash="unused", role="viewer")
        db.add(viewer); db.flush()
        tokens["a-viewer"] = create_access_token(db, viewer)
        db.commit()
    yield TestClient(app), tokens, organizations
    app.dependency_overrides.clear()
    engine.dispose()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_dashboards_and_graphs_are_tenant_isolated(tenant_app):
    client, tokens, _ = tenant_app
    a = client.get("/api/v1/dashboard/summary", headers=auth(tokens["a"]))
    b = client.get("/api/v1/dashboard/summary", headers=auth(tokens["b"]))
    assert a.status_code == b.status_code == 200
    assert a.json()["revenue"] == 100.0
    assert b.json()["revenue"] == 900.0
    assert a.json()["revenue_overview"] != b.json()["revenue_overview"]


def test_registration_creates_a_new_owner_and_organization(tenant_app, monkeypatch):
    client, _, _ = tenant_app
    delivered = {}
    monkeypatch.setattr("app.application.auth.otp_service.validate_mx_domain", lambda _: None)
    monkeypatch.setattr("app.application.auth.email_service.SmtpEmailService.send_otp", lambda _, email, code, purpose: delivered.__setitem__(email, code))
    organizations = []
    for suffix in ("a", "b"):
        email = f"new-{suffix}@example.com"
        requested = client.post("/api/v1/auth/register", json={"email": email, "full_name": f"New {suffix}", "organization_name": f"New Company {suffix}", "password": "SecurePass123!"})
        assert requested.status_code == 202 and "otp" not in requested.text.lower()
        verified = client.post("/api/v1/auth/register/verify-otp", json={"email": email, "otp": delivered[email]})
        assert verified.status_code == 201 and verified.json()["role"] == "owner"
        organizations.append(verified.json()["organization_id"])
    assert organizations[0] != organizations[1]


def test_paginated_apis_and_analytics_are_tenant_isolated(tenant_app):
    client, tokens, _ = tenant_app
    sales_a = client.get("/api/v1/sales", headers=auth(tokens["a"])).json()
    sales_b = client.get("/api/v1/sales", headers=auth(tokens["b"])).json()
    assert [item["order_number"] for item in sales_a["items"]] == ["ORDER-a"]
    assert [item["order_number"] for item in sales_b["items"]] == ["ORDER-b"]
    assert client.get("/api/v1/analytics/overview", headers=auth(tokens["a"])).json()["revenue"] == 100.0
    assert client.get("/api/v1/analytics/overview", headers=auth(tokens["b"])).json()["revenue"] == 900.0


def test_same_company_shares_reads_but_rbac_blocks_viewer_writes(tenant_app):
    client, tokens, _ = tenant_app
    owner_dashboard = client.get("/api/v1/dashboard/summary", headers=auth(tokens["a"])).json()
    viewer_dashboard = client.get("/api/v1/dashboard/summary", headers=auth(tokens["a-viewer"])).json()
    assert viewer_dashboard == owner_dashboard
    upload = client.post("/api/v1/files/uploads", headers={**auth(tokens["a-viewer"]), "X-Filename": "blocked.csv", "Content-Type": "text/csv"}, content=b"x\n1\n")
    report = client.post("/api/v1/files/reports", headers={**auth(tokens["a-viewer"]), "Content-Type": "application/json"}, json={})
    assert upload.status_code == report.status_code == 403


def test_owner_can_add_member_only_to_own_company(tenant_app):
    client, tokens, organizations = tenant_app
    created = client.post("/api/v1/auth/members", headers=auth(tokens["a"]), json={"email": "invited@example.com", "full_name": "Invited Viewer", "password": "SecurePass123!", "role": "viewer"})
    assert created.status_code == 201
    assert created.json()["organization_id"] == str(organizations["a"])
    login = client.post("/api/v1/auth/login", json={"email": "invited@example.com", "password": "SecurePass123!"})
    assert login.status_code == 200
    invited_dashboard = client.get("/api/v1/dashboard/summary", headers=auth(login.json()["access_token"]))
    assert invited_dashboard.json()["revenue"] == 100.0
    blocked = client.post("/api/v1/auth/members", headers=auth(tokens["a-viewer"]), json={"email": "blocked@example.com", "full_name": "Blocked", "password": "SecurePass123!", "role": "viewer"})
    assert blocked.status_code == 403


def test_uploads_and_direct_file_urls_reject_cross_tenant_access(tenant_app):
    client, tokens, _ = tenant_app
    csv_data = b"Date,Revenue,Orders,Cancelled,Region,Product,Customer\n2026-08-02,200,2,0,North,Tenant A Exclusive,Private Customer A\n"
    created = client.post("/api/v1/files/uploads", headers={**auth(tokens["a"]), "X-Filename": "private.csv", "Content-Type": "text/csv"}, content=csv_data)
    assert created.status_code == 201
    asset_id = created.json()["id"]
    assert client.get(f"/api/v1/files/{asset_id}/view", headers=auth(tokens["a"])).status_code == 200
    assert client.get(f"/api/v1/files/{asset_id}/view", headers=auth(tokens["b"])).status_code == 404
    assert client.get("/api/v1/files", headers=auth(tokens["b"])).json()["count"] == 0
    imported = client.post("/api/v1/datasets/imports", headers={**auth(tokens["a"]), "X-Filename": "tenant-a.csv", "X-Import-Mode": "append", "Content-Type": "text/csv"}, content=csv_data)
    assert imported.status_code == 202
    dataset = client.get("/api/v1/datasets/status", headers=auth(tokens["a"])).json()
    assert dataset["has_data"] is True and dataset["history"][0]["status"] == "completed"
    session_iterator = app.dependency_overrides[get_db]()
    db = next(session_iterator)
    try:
        imported_customer = db.query(Customer).filter(Customer.company_name == "Private Customer A").one()
        assert len(imported_customer.customer_number) <= Customer.__table__.c.customer_number.type.length
    finally:
        session_iterator.close()
    assert client.get("/api/v1/dashboard/summary", headers=auth(tokens["a"])).json()["revenue"] == 300.0
    assert client.get("/api/v1/dashboard/summary", headers=auth(tokens["b"])).json()["revenue"] == 900.0


def test_forged_organization_claim_is_rejected(tenant_app):
    client, tokens, organizations = tenant_app
    settings = get_settings()
    claims = jwt.decode(tokens["a"], settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    claims["org"] = str(organizations["b"])
    forged = jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    response = client.get("/api/v1/dashboard/summary", headers=auth(forged))
    assert response.status_code == 401


def test_pdf_reports_are_tenant_scoped_and_contain_different_analytics(tenant_app):
    client, tokens, _ = tenant_app
    report_a = client.post("/api/v1/files/reports", headers={**auth(tokens["a"]), "Content-Type": "application/json"}, json={})
    report_b = client.post("/api/v1/files/reports", headers={**auth(tokens["b"]), "Content-Type": "application/json"}, json={})
    assert report_a.status_code == report_b.status_code == 201
    id_a, id_b = report_a.json()["id"], report_b.json()["id"]
    pdf_a = client.get(f"/api/v1/files/{id_a}/view", headers=auth(tokens["a"]))
    pdf_b = client.get(f"/api/v1/files/{id_b}/view", headers=auth(tokens["b"]))
    assert pdf_a.status_code == pdf_b.status_code == 200
    assert pdf_a.content.startswith(b"%PDF") and pdf_b.content.startswith(b"%PDF")
    assert pdf_a.content != pdf_b.content
    assert client.get(f"/api/v1/files/{id_a}/download", headers=auth(tokens["b"])).status_code == 404


def test_dataset_initial_append_replace_delete_lifecycle(tenant_app):
    client, tokens, _ = tenant_app
    data = b"Date,Revenue,Orders,Cancelled,Region,Product,Customer\n2026-08-03,250,5,0,West,Lifecycle Product,Lifecycle Customer\n"
    base = {**auth(tokens["a"]), "X-Filename": "lifecycle.csv", "Content-Type": "text/csv"}
    assert client.post("/api/v1/datasets/imports", headers={**base, "X-Import-Mode": "initial"}, content=data).status_code == 409
    assert client.post("/api/v1/datasets/imports", headers={**base, "X-Import-Mode": "replace"}, content=data).status_code == 202
    assert client.get("/api/v1/dashboard/summary", headers=auth(tokens["a"])).json()["revenue"] == 250.0
    assert client.post("/api/v1/datasets/imports", headers={**base, "X-Import-Mode": "append"}, content=data).status_code == 202
    assert client.get("/api/v1/dashboard/summary", headers=auth(tokens["a"])).json()["revenue"] == 500.0
    assert client.delete("/api/v1/datasets/current", headers=auth(tokens["a"])).status_code == 204
    status_payload = client.get("/api/v1/datasets/status", headers=auth(tokens["a"])).json()
    assert status_payload["has_data"] is False and status_payload["record_count"] == 0


def test_sentinel_ai_is_grounded_persistent_and_tenant_isolated(tenant_app):
    client, tokens, _ = tenant_app
    answer_a = client.post("/api/v1/ai/chat", headers=auth(tokens["a"]), json={"message": "Show total revenue"})
    answer_b = client.post("/api/v1/ai/chat", headers=auth(tokens["b"]), json={"message": "Show total revenue"})
    assert answer_a.status_code == answer_b.status_code == 200
    assert "$100.00" in answer_a.json()["message"]["content"]
    assert "$900.00" in answer_b.json()["message"]["content"]
    conversation_id = answer_a.json()["conversation_id"]
    follow_up = client.post("/api/v1/ai/chat", headers=auth(tokens["a"]), json={"conversation_id": conversation_id, "message": "Which product performed best?"})
    assert follow_up.status_code == 200 and "Product a" in follow_up.json()["message"]["content"]
    history = client.get(f"/api/v1/ai/conversations/{conversation_id}", headers=auth(tokens["a"]))
    assert history.status_code == 200 and len(history.json()["messages"]) == 4
    assert client.get(f"/api/v1/ai/conversations/{conversation_id}", headers=auth(tokens["b"])).status_code == 404
    assert client.delete(f"/api/v1/ai/conversations/{conversation_id}", headers=auth(tokens["b"])).status_code == 404


def test_forecast_anomalies_and_ai_failures_are_safe(tenant_app):
    client, tokens, _ = tenant_app
    assert client.get("/api/v1/ai/forecast?horizon_days=30", headers=auth(tokens["a"])).status_code == 200
    assert client.get("/api/v1/ai/anomalies", headers=auth(tokens["a"])).status_code == 200
    assert client.post("/api/v1/ai/chat", headers=auth(tokens["a"]), json={"message": ""}).status_code == 422
    assert client.post("/api/v1/ai/chat", json={"message": "Show revenue"}).status_code == 401


def test_invitations_audit_logs_and_scheduled_reports_work(tenant_app):
    client, tokens, organizations = tenant_app
    invitation = client.post("/api/v1/governance/invitations", headers=auth(tokens["a"]), json={"email": "team@example.com", "role": "viewer"})
    assert invitation.status_code == 201
    accepted = client.post("/api/v1/governance/invitations/accept", json={"token": invitation.json()["token"], "full_name": "Team Viewer", "password": "SecurePass123!"})
    assert accepted.status_code == 201 and accepted.json()["organization_id"] == str(organizations["a"])
    assert client.post("/api/v1/governance/invitations", headers=auth(tokens["a-viewer"]), json={"email": "blocked2@example.com", "role": "viewer"}).status_code == 403
    schedule = client.post("/api/v1/governance/report-schedules", headers=auth(tokens["a"]), json={"name": "Weekly executive report", "frequency": "weekly"})
    assert schedule.status_code == 201
    run = client.post(f"/api/v1/governance/report-schedules/{schedule.json()['id']}/run", headers=auth(tokens["a"]))
    assert run.status_code == 200
    assert client.get(run.json()["view_url"], headers=auth(tokens["a"])).content.startswith(b"%PDF")
    assert client.get(run.json()["view_url"], headers=auth(tokens["b"])).status_code == 404
    logs = client.get("/api/v1/governance/audit-logs", headers=auth(tokens["a"])).json()
    assert any(item["action"] == "report_schedule.run" for item in logs)


def test_excel_signature_and_invalid_uploads_are_rejected(tenant_app):
    client, tokens, _ = tenant_app
    invalid_excel = client.post("/api/v1/datasets/imports", headers={**auth(tokens["a"]), "X-Filename": "fake.xlsx", "X-Import-Mode": "append", "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}, content=b"not-an-excel-workbook")
    assert invalid_excel.status_code == 422
    traversal = client.post("/api/v1/files/uploads", headers={**auth(tokens["a"]), "X-Filename": "../../secret.pdf", "Content-Type": "application/pdf"}, content=b"not-pdf")
    assert traversal.status_code == 422
    missing = client.get(f"/api/v1/files/{uuid4()}/download", headers=auth(tokens["a"]))
    assert missing.status_code == 404


def test_sentinel_handles_normal_conversation_without_a_dataset(tenant_app):
    client, tokens, _ = tenant_app
    prompts = {
        "Hi": "Hi! I'm Sentinel AI",
        "Hello, what can you do?": "uploaded CSV or Excel datasets",
        "What is Sentinel?": "tenant-isolated business intelligence platform",
        "Thank you": "You're welcome",
        "How are you?": "I'm doing well",
    }
    conversation_id = None
    for prompt, expected in prompts.items():
        response = client.post("/api/v1/ai/chat", headers=auth(tokens["a"]), json={"message": prompt, "conversation_id": conversation_id})
        assert response.status_code == 200
        assert expected in response.json()["message"]["content"]
        conversation_id = response.json()["conversation_id"]


def test_sentinel_calculates_exact_values_from_uploaded_file(tenant_app):
    client, tokens, _ = tenant_app
    data = b"Date,Revenue,Orders,Cancelled,Region,Product,Customer\n2026-08-01,250000,25,2,North,Sentinel Core,Acme Corporation\n2026-08-02,100000,10,1,South,Sentinel Edge,Beta Limited\n"
    imported = client.post("/api/v1/datasets/imports", headers={**auth(tokens["a"]), "X-Filename": "sentinel-exact.csv", "X-Import-Mode": "replace", "Content-Type": "text/csv"}, content=data)
    assert imported.status_code == 202
    sentiment = client.get("/api/v1/dashboard/summary", headers=auth(tokens["a"])).json()
    assert sentiment["sentiment_available"] is False
    assert sentiment["sentiment_score"] is None and "unavailable" in sentiment["sentiment_message"].lower()
    questions = {
        "Summarize this file.": ["350,000.00", "35", "3", "North", "Sentinel Core"],
        "What is the total revenue?": ["350,000.00"],
        "Which region has the highest revenue?": ["North", "250,000.00"],
        "Which product performed best?": ["Sentinel Core", "250,000.00"],
        "How many orders were cancelled?": ["3 cancelled orders"],
        "Show the top 2 customers": ["Acme Corporation", "Beta Limited"],
    }
    for question, expected_values in questions.items():
        response = client.post("/api/v1/ai/chat", headers=auth(tokens["a"]), json={"message": question})
        assert response.status_code == 200
        answer = response.json()["message"]["content"]
        assert all(value in answer for value in expected_values), (question, answer)
    unavailable = client.post("/api/v1/ai/chat", headers=auth(tokens["a"]), json={"message": "What is our advertising spend?"})
    assert unavailable.status_code == 200
    assert "need a little more context" in unavailable.json()["message"]["content"]
    tenant_b = client.post("/api/v1/ai/chat", headers=auth(tokens["b"]), json={"message": "Analyze sentinel-exact.csv total revenue"})
    assert tenant_b.status_code == 200
    assert "350,000.00" not in tenant_b.json()["message"]["content"]


def test_real_otp_security_flows_and_session_revocation(tenant_app, monkeypatch):
    client, tokens, _ = tenant_app
    delivered = {}
    monkeypatch.setattr("app.application.auth.email_service.SmtpEmailService.send_otp", lambda _, email, code, purpose: delivered.__setitem__((email, purpose), code))
    request_login = client.post("/api/v1/auth/otp-login/request", json={"email": "owner-a@example.com"})
    assert request_login.status_code == 202 and "otp" not in request_login.text.lower()
    assert client.post("/api/v1/auth/otp-login/request", json={"email": "owner-a@example.com"}).status_code == 429
    wrong = client.post("/api/v1/auth/otp-login/verify", json={"email": "owner-a@example.com", "otp": "Z9Z9Z9"})
    assert wrong.status_code == 400
    code = delivered[("owner-a@example.com", "login")]
    verified = client.post("/api/v1/auth/otp-login/verify", json={"email": "owner-a@example.com", "otp": code})
    assert verified.status_code == 200 and verified.json()["access_token"]
    assert client.get("/api/v1/dashboard/summary", headers=auth(verified.json()["access_token"])).status_code == 200
    assert client.post("/api/v1/auth/otp-login/verify", json={"email": "owner-a@example.com", "otp": code}).status_code == 400

    reset_request = client.post("/api/v1/auth/password/request-otp", json={"email": "owner-a@example.com"})
    assert reset_request.status_code == 202
    reset_code = delivered[("owner-a@example.com", "password_reset")]
    reset_verify = client.post("/api/v1/auth/password/verify-otp", json={"email": "owner-a@example.com", "otp": reset_code})
    assert reset_verify.status_code == 200 and reset_verify.json()["reset_token"]
    reset = client.post("/api/v1/auth/password/reset", json={"reset_token": reset_verify.json()["reset_token"], "new_password": "ChangedPass123!"})
    assert reset.status_code == 200
    latest_login = client.post("/api/v1/auth/login", json={"email": "owner-a@example.com", "password": "ChangedPass123!"})
    assert latest_login.status_code == 200
    assert client.post("/api/v1/auth/password/reset", json={"reset_token": reset_verify.json()["reset_token"], "new_password": "AnotherPass123!"}).status_code == 400

    latest_token = latest_login.json()["access_token"]
    assert client.post("/api/v1/auth/logout", headers=auth(latest_token)).status_code == 204
    assert client.get("/api/v1/dashboard/summary", headers=auth(latest_token)).status_code == 401
    remembered = client.post("/api/v1/auth/login", json={"email": "owner-a@example.com", "password": "ChangedPass123!", "remember": True})
    remembered_claims = jwt.decode(remembered.json()["access_token"], get_settings().jwt_secret_key, algorithms=[get_settings().jwt_algorithm])
    assert datetime.fromtimestamp(remembered_claims["exp"], UTC) - datetime.now(UTC) > timedelta(days=6)
    nonexistent = client.post("/api/v1/auth/password/request-otp", json={"email": "absent@example.com"})
    assert nonexistent.status_code == 202 and "If an account exists" in nonexistent.json()["message"]


def test_returning_login_preserves_tenant_workspace(tenant_app):
    client, tokens, _ = tenant_app
    member = client.post(
        "/api/v1/auth/members",
        headers=auth(tokens["a"]),
        json={"email": "session-owner@example.com", "full_name": "Session Owner", "password": "SessionPass123!", "role": "manager"},
    )
    assert member.status_code == 201
    first_login = client.post("/api/v1/auth/login", json={"email": "session-owner@example.com", "password": "SessionPass123!"})
    assert first_login.status_code == 200
    first_token = first_login.json()["access_token"]
    assert client.get("/api/v1/datasets/status", headers=auth(first_token)).json()["has_data"] is True

    file_a = b"Date,Revenue,Orders,Cancelled,Region,Product,Customer\n2026-08-01,111,3,0,North,File A Product,File A Customer\n"
    imported_a = client.post("/api/v1/datasets/imports", headers={**auth(first_token), "X-Filename": "file-a.csv", "X-Import-Mode": "replace", "Content-Type": "text/csv"}, content=file_a)
    assert imported_a.status_code == 202
    report = client.post("/api/v1/files/reports", headers={**auth(first_token), "Content-Type": "application/json"}, json={})
    chat = client.post("/api/v1/ai/chat", headers=auth(first_token), json={"message": "Show total revenue"})
    assert report.status_code == 201 and chat.status_code == 200
    assert client.get("/api/v1/dashboard/summary", headers=auth(first_token)).json()["revenue"] == 111.0
    report_id = report.json()["id"]

    assert client.post("/api/v1/auth/logout", headers=auth(first_token)).status_code == 204
    assert client.get("/api/v1/dashboard/summary", headers=auth(first_token)).status_code == 401

    second_login = client.post("/api/v1/auth/login", json={"email": "session-owner@example.com", "password": "SessionPass123!"})
    assert second_login.status_code == 200
    second_token = second_login.json()["access_token"]
    status_payload = client.get("/api/v1/datasets/status", headers=auth(second_token)).json()
    assert status_payload["has_data"] is True and status_payload["record_count"] == 1
    assert status_payload["history"][0]["status"] == "completed"
    assert client.get("/api/v1/files", headers=auth(second_token)).json()["count"] >= 2
    assert client.get("/api/v1/ai/conversations", headers=auth(second_token)).json()
    assert client.get(f"/api/v1/files/{report_id}/view", headers=auth(second_token)).status_code == 200
    assert client.get("/api/v1/dashboard/summary", headers=auth(second_token)).json()["revenue"] == 111.0


def test_sentiment_risk_and_natural_language_are_dataset_grounded(tenant_app):
    client, tokens, _ = tenant_app
    member = client.post("/api/v1/auth/members", headers=auth(tokens["a"]), json={"email": "analyst@example.com", "full_name": "Risk Analyst", "password": "AnalystPass123!", "role": "manager"})
    assert member.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": "analyst@example.com", "password": "AnalystPass123!"})
    token = login.json()["access_token"]
    data = (
        b"Date,Revenue,Orders,Cancelled,Region,Product,Customer,Rating,Feedback\n"
        b"2026-08-01,1000,10,0,North,Sentinel Core,Acme,1,Terrible delays and poor service\n"
        b"2026-08-02,800,10,1,North,Sentinel Core,Acme,2,Disappointed with the product\n"
        b"2026-08-03,400,10,2,South,Sentinel Core,Acme,2,Slow and unreliable\n"
        b"2026-08-04,200,10,3,South,Sentinel Edge,Beta,1,Very bad experience\n"
    )
    imported = client.post("/api/v1/datasets/imports", headers={**auth(token), "X-Filename": "risk-negative.csv", "X-Import-Mode": "replace", "Content-Type": "text/csv"}, content=data)
    assert imported.status_code == 202
    dashboard = client.get("/api/v1/dashboard/summary", headers=auth(token)).json()
    assert dashboard["sentiment_available"] is True
    assert dashboard["sentiment_label"] == "Negative" and dashboard["sentiment_score"] < 40
    assert dashboard["customer_sentiment"] != []

    questions = {
        "Hi": "Hi! I'm Sentinel AI",
        "What can you do?": "analyze uploaded CSV or Excel datasets",
        "Summarize my data.": "Total revenue:** 2,400.00",
        "What is total revenue?": "2,400.00",
        "Which product performed best?": "Sentinel Core",
        "Which region performed worst?": "South",
        "What are the risks?": "Revenue Risk",
        "Give me a complete risk analysis.": "Order Risk",
        "What should I worry about?": "Customer Concentration Risk",
        "Are there unusual patterns?": "Risk analysis",
        "What is my customer sentiment?": "Negative",
        "Why is sentiment negative?": "12.5/100",
        "What data supports that conclusion?": "Evidence:",
        "Give me recommendations.": "Recommendation:",
    }
    conversation_id = None
    for question, expected in questions.items():
        response = client.post("/api/v1/ai/chat", headers=auth(token), json={"message": question, "conversation_id": conversation_id})
        assert response.status_code == 200, (question, response.text)
        assert expected in response.json()["message"]["content"], (question, response.json()["message"]["content"])
        conversation_id = response.json()["conversation_id"]

    positive = (
        b"Date,Revenue,Orders,Cancelled,Region,Product,Customer,Rating,Feedback\n"
        b"2026-08-05,500,5,0,West,Sentinel Edge,Gamma,5,Excellent service and amazing product\n"
        b"2026-08-06,600,6,0,West,Sentinel Edge,Gamma,5,Very happy and satisfied\n"
    )
    replaced = client.post("/api/v1/datasets/imports", headers={**auth(token), "X-Filename": "positive.csv", "X-Import-Mode": "replace", "Content-Type": "text/csv"}, content=positive)
    assert replaced.status_code == 202
    changed = client.get("/api/v1/dashboard/summary", headers=auth(token)).json()
    assert changed["sentiment_label"] == "Positive" and changed["sentiment_score"] > dashboard["sentiment_score"]


def test_otp_expiration_and_maximum_attempts(tenant_app, monkeypatch):
    client, _, _ = tenant_app
    delivered = {}
    monkeypatch.setattr("app.application.auth.email_service.SmtpEmailService.send_otp", lambda _, email, code, purpose: delivered.__setitem__((email, purpose), code))
    settings = get_settings()
    original_expiry, original_attempts = settings.otp_expire_minutes, settings.otp_max_attempts
    settings.otp_expire_minutes = -1
    assert client.post("/api/v1/auth/otp-login/request", json={"email": "owner-b@example.com"}).status_code == 202
    expired_code = delivered[("owner-b@example.com", "login")]
    assert client.post("/api/v1/auth/otp-login/verify", json={"email": "owner-b@example.com", "otp": expired_code}).status_code == 400
    settings.otp_expire_minutes = 10
    settings.otp_max_attempts = 2
    assert client.post("/api/v1/auth/password/request-otp", json={"email": "owner-b@example.com"}).status_code == 202
    for _ in range(2): assert client.post("/api/v1/auth/password/verify-otp", json={"email": "owner-b@example.com", "otp": "Z9Z9Z9"}).status_code == 400
    assert client.post("/api/v1/auth/password/verify-otp", json={"email": "owner-b@example.com", "otp": delivered[("owner-b@example.com", "password_reset")]}).status_code == 429
    settings.otp_expire_minutes, settings.otp_max_attempts = original_expiry, original_attempts
