from oracle_data.models import WardrobeItem
from django.utils import timezone
from operator import itemgetter


def fetch_user_wardrobe(user_id):
    items = WardrobeItem.objects.filter(user_id=user_id)
    return [
        {
            "name": item.name,
            "category": item.category,
            "season": item.season,   
            "favorite": item.is_favorite,  
            "usage": item.last_used  
        }
        for item in items
    ]


# def get_sorted_wardrobe(user_id):
#     wardrobe = fetch_user_wardrobe(user_id)
    
#     now = timezone.now()
#     for item in wardrobe:
#         last_used = item["usage"]
#         if last_used:
#             days_since_used = (now - last_used).days
#         else:
#             days_since_used = 999  

#         item["staleness_score"] = days_since_used

#     return sorted(wardrobe, key=itemgetter("staleness_score"), reverse=True)

def get_serialized_wardrobe(user_id):
    items = WardrobeItem.objects.filter(user_id=user_id).order_by("-is_favorite", "-added_at")
    serialized = []
    for item in items:
        serialized.append({
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "color": item.color,
            "style_tags": item.style_tags,
            "season": item.season,
            "is_favorite": item.is_favorite,
            # Add more if needed, but exclude `added_at`, `last_used`, or any binary/image fields
        })
    return serialized

