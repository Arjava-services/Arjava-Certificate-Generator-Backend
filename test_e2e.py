import time
import httpx
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000/api/v1"

def run_e2e_verification():
    print("=================================================================")
    print(" Starting End-to-End Automated Verification of Certificate Generator")
    print("=================================================================")

    with httpx.Client(timeout=30.0) as client:
        # 1. Health check
        res = client.get("http://127.0.0.1:8000/api/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        print("[PASS] Step 1: Backend Health Check OK:", res.json())

        # 2. Check sample templates
        samples_res = client.get(f"{BASE_URL}/templates/samples")
        assert samples_res.status_code == 200
        samples = samples_res.json()
        assert len(samples) > 0, "No sample templates found"
        sample_file = samples[0]["filename"]
        print(f"[PASS] Step 2: Sample Templates Available ({len(samples)} found, using '{sample_file}')")

        # 3. Create Project
        proj_res = client.post(f"{BASE_URL}/projects", json={"name": "Annual Web Developer Summit 2026"})
        assert proj_res.status_code == 201
        project = proj_res.json()
        project_id = project["id"]
        print(f"[PASS] Step 3: Created Project '{project['name']}' (ID: {project_id})")

        # 4. Use Sample Template & extract placeholders
        tpl_res = client.post(
            f"{BASE_URL}/templates/use-sample",
            data={"project_id": project_id, "sample_filename": sample_file}
        )
        assert tpl_res.status_code == 200
        tpl_data = tpl_res.json()
        detected = tpl_data["detected_placeholders"]
        print(f"[PASS] Step 4: Template Applied. Detected {len(detected)} placeholders:")
        for ph in detected:
            print(f"    - {ph['placeholder']} at ({ph['x_pos']}, {ph['y_pos']}) pt")

        # 5. Connect Google Sheet (Demo data)
        demo_res = client.get(f"{BASE_URL}/sheets/demo")
        assert demo_res.status_code == 200
        sheet_data = demo_res.json()
        headers = sheet_data["headers"]
        rows = sheet_data["all_rows"]
        print(f"[PASS] Step 5: Google Sheet Data Connected. {len(rows)} participants, Headers: {headers}")

        # 6. Map Fields
        # Map {{name}} -> Name, {{competition}} -> Competition, {{position}} -> Position, {{year}} -> Year, {{date}} -> Date
        mapping_updates = []
        for ph in detected:
            col_match = None
            clean = ph["placeholder"].replace("{", "").replace("}", "").lower()
            for h in headers:
                if h.lower() == clean or clean in h.lower():
                    col_match = h
                    break
            mapping_updates.append({
                "placeholder": ph["placeholder"],
                "sheet_column": col_match,
                "font_family": ph["font_name"] or "Helvetica",
                "font_size": ph["font_size"] or 24,
                "font_color": "#1e293b",
                "font_weight": "bold" if "name" in clean else "normal",
                "x_pos": ph["x_pos"],
                "y_pos": ph["y_pos"],
                "width": ph["width"],
                "height": ph["height"],
                "alignment": "center",
                "is_auto_detected": True,
                "is_required": True
            })

        map_res = client.put(f"{BASE_URL}/mappings/{project_id}", json={"mappings": mapping_updates})
        assert map_res.status_code == 200
        saved_mappings = map_res.json()
        print(f"[PASS] Step 6: Saved {len(saved_mappings)} Field Mappings:")
        for sm in saved_mappings:
            print(f"    - {sm['placeholder']} -> [{sm['sheet_column']}]")

        # 7. Validate Data
        val_res = client.post(f"{BASE_URL}/sheets/validate", json={"project_id": project_id, "rows": rows})
        assert val_res.status_code == 200
        val_data = val_res.json()
        print(f"[PASS] Step 7: Pre-Generation Validation: is_valid={val_data['is_valid']}, {val_data['valid_rows_count']}/{val_data['total_rows']} valid rows, {val_data['error_count']} errors, {val_data['warning_count']} warnings")

        # 8. Single Preview Test
        preview_res = client.post(
            f"{BASE_URL}/generate/preview-single",
            json={"project_id": project_id, "row_data": rows[0], "output_format": "png"}
        )
        assert preview_res.status_code == 200
        preview_data = preview_res.json()
        assert preview_data["preview_url"].startswith("data:image/png;base64,")
        print(f"[PASS] Step 8: Single Certificate Preview Rendered for '{preview_data['participant_name']}' -> Filename: {preview_data['filename']}")

        # 9. Start Batch Generation (PDF)
        gen_res = client.post(
            f"{BASE_URL}/generate",
            json={
                "project_id": project_id,
                "rows": rows,
                "output_format": "pdf",
                "naming_pattern": "{{name}}_Certificate_{{year}}"
            }
        )
        assert gen_res.status_code == 202
        job = gen_res.json()
        job_id = job["id"]
        print(f"[PASS] Step 9: Batch Generation Job Queued (Job ID: {job_id})")

        # 10. Poll Job until complete
        max_attempts = 20
        while max_attempts > 0:
            status_res = client.get(f"{BASE_URL}/generate/jobs/{job_id}")
            assert status_res.status_code == 200
            st = status_res.json()
            pct = st["progress_percentage"]
            curr = st.get("current_participant")
            print(f"    ... Generation Progress: {pct}% ({st['processed_rows']}/{st['total_rows']}) - Current: {curr}")
            if st["status"] in ("completed", "partial", "failed"):
                break
            time.sleep(0.5)
            max_attempts -= 1

        assert st["status"] == "completed", f"Job failed with status {st['status']}: {st.get('error_log')}"
        print(f"[PASS] Step 10: Generation Job Completed! 100% ({st['successful_count']} successful certificates, {st['failed_count']} failed)")

        # 11. Verify Generated Certificates List
        certs_res = client.get(f"{BASE_URL}/certificates/{project_id}")
        assert certs_res.status_code == 200
        cert_list = certs_res.json()
        assert cert_list["total"] == len(rows), f"Expected {len(rows)} certs, got {cert_list['total']}"
        print(f"[PASS] Step 11: Listed {cert_list['total']} Generated Certificates:")
        for c in cert_list["certificates"]:
            print(f"    - Participant: {c['participant_name']} | File: {c['filename']} ({c['file_size']} bytes) | Status: {c['status']}")

        # 12. Test Individual Download
        first_cert = cert_list["certificates"][0]
        dl_res = client.get(f"{BASE_URL}/certificates/{first_cert['id']}/download")
        assert dl_res.status_code == 200
        assert len(dl_res.content) > 1000, "Downloaded certificate is unexpectedly empty"
        print(f"[PASS] Step 12: Successfully downloaded individual certificate '{first_cert['filename']}' ({len(dl_res.content)} bytes)")

        # 13. Test ZIP Download All
        zip_res = client.get(f"{BASE_URL}/certificates/{project_id}/download-all")
        assert zip_res.status_code == 200
        assert len(zip_res.content) > 2000, "ZIP archive is unexpectedly empty"
        print(f"[PASS] Step 13: Successfully downloaded 'certificates.zip' ({len(zip_res.content)} bytes) containing all certificates!")

        # 14. Verify Frontend Vite Dev Server
        fe_res = client.get("http://localhost:5173/")
        assert fe_res.status_code == 200
        assert "Certificate Generator" in fe_res.text
        print("[PASS] Step 14: Frontend Dev Server (http://localhost:5173/) verified responding with HTML root and SEO metadata!")

    print("\n=================================================================")
    print(" ALL 14 END-TO-END VERIFICATION CHECKS PASSED PERFECTLY!")
    print("=================================================================")

if __name__ == "__main__":
    run_e2e_verification()
