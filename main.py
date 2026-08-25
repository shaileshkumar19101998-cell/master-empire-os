@app.get("/api/download/{order_id}")
def download_secure_book(order_id: str, request: Request, token: Optional[str] = None):
    oid_clean = str(order_id).strip()
    if not token or not verify_signed_download_token(token, oid_clean):
        raise HTTPException(status_code=403, detail="Download authorization token is invalid or expired.")

    try:
        with engine.connect() as conn:
            order = conn.execute(text("SELECT * FROM orders WHERE id = :oid"), {"oid": oid_clean}).mappings().first()
            if not order or order["status"] != "PAID":
                raise HTTPException(status_code=403, detail="Access denied: Unsettled or missing order.")

            product = conn.execute(text("SELECT * FROM products WHERE id = :pid"), {"pid": order["product_id"]}).mappings().first()
            pdf_path = product["pdf_file_path"] if product and product["pdf_file_path"] else "books/saas/v1.pdf"

        # 1. यदि लोकल फ़ाइल सिस्टम में असली PDF मौजूद है:
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                real_pdf_bytes = f.read()
            return PlainResponse(
                content=real_pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=SaaS_Architecture_Handbook.pdf"}
            )

        # 2. फ़ाइल न मिलने पर साफ़ एरर
        raise HTTPException(
            status_code=503, 
            detail="Digital asset repository currently synchronizing. Please retry in 60 seconds."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
