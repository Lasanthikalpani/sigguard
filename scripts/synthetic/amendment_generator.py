# scripts/synthetic/amendment_generator.py

def create_amendment(original_record: dict, amendment_reason: str) -> dict:
    """Layer 5: legit amendment with amends pointer."""
    new_record = original_record.copy()
    new_record["document_id"] = original_record["document_id"].replace(
        "BC-", f"BC-{2026}-")
    new_record["document_type"] = "AMENDED"
    new_record["amends"] = original_record["document_id"]
    
    if amendment_reason == "surname_change":
        old_name = original_record["name"]
        new_record["name"] = "Wickramasinghe " + old_name.split()[-1]
        new_record["content_text"] = new_record["content_text"].replace(
            old_name, new_record["name"])
    
    return new_record