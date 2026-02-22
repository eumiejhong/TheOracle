import django
from django.conf import settings
import os
import sys
from sentence_transformers import SentenceTransformer
from datetime import datetime

# Adding Django project to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oracle_backend.settings')
django.setup()

from oracle_data.models import UserStyleProfile, DailyStyleInput
from oracle_frontend.utils import combine_style_summary  
from oracle_frontend.archetype_generator import generate_style_archetype, generate_today_styling_suggestion

# Load BGE embedding model
bge = SentenceTransformer("BAAI/bge-base-en-v1.5")

def save_style_profile(profile: dict, user_id: str):
    appearance = profile["appearance"]
    lifestyle = profile["lifestyle"]
    style_identity = profile["style_identity"]

    # Combine summary for embedding
    summary = combine_style_summary(profile)

    # Embed it
    embedding = bge.encode(summary, normalize_embeddings=True)
    embedding_bytes = embedding.tobytes()

    style_archetype = generate_style_archetype(summary, user_id)
    print("📜 Archetype response:", style_archetype)

    existing = UserStyleProfile.objects.filter(user_id=user_id).first()
    if existing:
        existing.raw_text = summary
        existing.embedding = embedding_bytes
        existing.appearance = appearance
        existing.style_identity = style_identity
        existing.lifestyle = lifestyle
        existing.style_archetype = style_archetype
        existing.save()
    else:
        UserStyleProfile.objects.create(
            user_id=user_id,
            raw_text=summary,
            embedding=embedding_bytes,
            appearance=appearance,
            style_identity=style_identity,
            lifestyle=lifestyle,
            style_archetype=style_archetype
        )



def save_daily_input(user_id: str, daily_context: dict, model_name: str = "gpt-4o"):
    try:
        profile = UserStyleProfile.objects.filter(user_id=user_id).latest("created_at")
    except UserStyleProfile.DoesNotExist:
        raise ValueError("No base style profile found for this user.")

    today = datetime.now().date()

    existing_entry = DailyStyleInput.objects.filter(
        user_profile=profile,
        created_at__date=today
    ).first()

    summary_text = combine_style_summary({
        "user_id": profile.user_id,
        "appearance": profile.appearance,
        "style_identity": profile.style_identity,
        "lifestyle": profile.lifestyle
    })

    outfit_suggestion = generate_today_styling_suggestion(summary_text, daily_context)

    if existing_entry:
        # Update existing entry
        existing_entry.mood_today = daily_context.get("mood_today", "")
        existing_entry.occasion = daily_context.get("occasion", "")
        existing_entry.weather = daily_context.get("weather", "")
        existing_entry.item_focus = daily_context.get("item_focus", "")
        existing_entry.outfit_suggestion = outfit_suggestion
        existing_entry.save()
    else:
        # Create a new one
        DailyStyleInput.objects.create(
            user_profile=profile,
            mood_today=daily_context.get("mood_today", ""),
            occasion=daily_context.get("occasion", ""),
            weather=daily_context.get("weather", ""),
            item_focus=daily_context.get("item_focus", ""),
            outfit_suggestion=outfit_suggestion
        )

    return outfit_suggestion

