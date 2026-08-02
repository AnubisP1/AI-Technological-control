from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_part_application_classes_returns_uav_domain_classes():
    response = client.get("/print/part-application-classes")

    assert response.status_code == 200
    codes = [item["code"] for item in response.json()]
    assert "PROPELLER" in codes
    assert "MOTOR_MOUNT" in codes


def test_list_operating_conditions_scoped_to_class():
    response = client.get(
        "/print/operating-conditions", params={"part_application_class_code": "PROPELLER"}
    )

    assert response.status_code == 200
    codes = [item["code"] for item in response.json()]
    assert "VIBRATION_HIGH_MOTOR_MOUNT" in codes


def test_list_operating_conditions_without_class_returns_full_reference():
    response = client.get("/print/operating-conditions")

    assert response.status_code == 200
    assert len(response.json()) >= 10


def test_list_operating_conditions_404_for_unknown_class():
    response = client.get(
        "/print/operating-conditions", params={"part_application_class_code": "WARP_DRIVE"}
    )

    assert response.status_code == 404


def test_material_recommendations_endpoint_returns_ranked_options_with_source_info():
    response = client.post(
        "/print/material-recommendations",
        params={
            "part_application_class_code": "PROPELLER",
            "operating_condition_codes": ["VIBRATION_HIGH_MOTOR_MOUNT"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["part_application_class_code"] == "PROPELLER"
    assert len(body["options"]) > 0
    top = body["options"][0]
    assert top["material_group_code"] == "NYLON_FDM"
    assert top["source_type"] in ("community_practice", "manufacturer_datasheet")
    assert top["source_reliability"] in ("low", "medium", "high")
    assert body["warnings"] == []


def test_material_recommendations_endpoint_without_conditions_uses_query_default():
    """operating_condition_codes не передан вовсе — Query(default=[])
    не должен требовать параметр (иначе фронтенд обязан был бы всегда
    сначала запрашивать типичные условия, даже когда хочет базовую
    рекомендацию без уточнения)."""
    response = client.post(
        "/print/material-recommendations",
        params={"part_application_class_code": "PROPELLER"},
    )

    assert response.status_code == 200
