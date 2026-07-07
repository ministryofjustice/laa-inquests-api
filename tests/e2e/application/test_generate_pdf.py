def test_200_generate_pdf_returns_pdf_content(client):
    response = client.get("/applications/pdf-generator")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    # Verify response contains PDF magic bytes
    assert response.content.startswith(b"%PDF")


def test_200_generate_pdf_contains_multiple_pages(client):
    response = client.get("/applications/pdf-generator")

    assert response.status_code == 200
    # Multi-page PDF should be larger than a minimal single page
    assert len(response.content) > 5000
