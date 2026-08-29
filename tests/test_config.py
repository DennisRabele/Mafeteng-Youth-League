from app.core.config import _normalize_database_url


def test_normalize_database_url_adds_system_root_cert_for_cockroach_cloud_verify_full():
    url = (
        "postgresql://sepirite:secret@peppy-condor-31282.j77.aws-eu-west-1.cockroachlabs.cloud:26257/defaultdb"
        "?sslmode=verify-full"
    )

    normalized = _normalize_database_url(url)

    assert normalized.startswith("cockroachdb+psycopg://")
    assert "sslmode=verify-full" in normalized
    assert "sslrootcert=system" in normalized


def test_normalize_database_url_leaves_require_mode_unchanged():
    url = (
        "postgresql+psycopg://sepirite:secret@peppy-condor-31282.j77.aws-eu-west-1.cockroachlabs.cloud:26257/defaultdb"
        "?sslmode=require"
    )

    normalized = _normalize_database_url(url)

    assert normalized == (
        "cockroachdb+psycopg://sepirite:secret@peppy-condor-31282.j77.aws-eu-west-1.cockroachlabs.cloud:26257/defaultdb"
        "?sslmode=require"
    )


def test_normalize_database_url_preserves_existing_sslrootcert():
    url = (
        "cockroachdb+psycopg://sepirite:secret@peppy-condor-31282.j77.aws-eu-west-1.cockroachlabs.cloud:26257/defaultdb"
        "?sslmode=verify-full&sslrootcert=/tmp/root.crt"
    )

    normalized = _normalize_database_url(url)

    assert normalized == url
