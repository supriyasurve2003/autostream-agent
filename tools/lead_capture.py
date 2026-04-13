from datetime import datetime


def mock_lead_capture(name: str, email: str, platform: str) -> dict:
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # In production we used database
    print(f"\n{'='*55}")
    print(f"  ✅  LEAD CAPTURED SUCCESSFULLY")
    print(f"{'='*55}")
    print(f"  Name     : {name}")
    print(f"  Email    : {email}")
    print(f"  Platform : {platform}")
    print(f"  Time     : {timestamp}")
    print(f"{'='*55}\n")

    return {
        "status": "success",
        "message": (
            f"Lead captured for {name} ({email}) on {platform} at {timestamp}."
        ),
    }
