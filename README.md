# The Oracle

**An AI-powered personal styling assistant that understands clothing as a mirror of emotion, movement, and identity.**

The Oracle is not a trend recommendation engine. It is a context-aware styling system that reads a user's aesthetic sensibility, wardrobe reality, and daily emotional state to generate outfit suggestions grounded in what they already own. It speaks in prose, not bullet points — treating personal style as a form of self-expression rather than a problem to be optimised.

---

## Motivation

Most fashion technology treats clothing as a classification problem: match colors, follow rules, replicate trends. But the way people actually dress is shaped by mood, weather, life transitions, body image, cultural context, and the specific garments hanging in their closet. The Oracle is an experiment in building a styling system that accounts for all of this — one that can hold the tension between "I want to feel powerful" and "I only have 20 minutes and it's raining."

This project explores several questions at the intersection of AI, fashion, and personal identity:

- Can large language models develop coherent aesthetic judgment when given structured context about a person's style psyche?
- How should wardrobe data be structured to enable meaningful outfit composition (beyond simple category matching)?
- What does it mean for an AI system to have *taste* — and how do you engineer that through prompt design, context architecture, and fine-tuning?

---

## How It Works

### 1. Style Profiling

Users complete a structured intake covering three dimensions:

- **Appearance** — skin tone, contrast level, undertone (informing color and material recommendations)
- **Style Identity** — archetype preferences, silhouette affinities, texture sensitivities, style constraints, aspirational references
- **Lifestyle** — mobility patterns, climate, formality level, wardrobe phase, budget, shopping behavior

This profile is embedded using [BGE (BAAI/bge-base-en-v1.5)](https://huggingface.co/BAAI/bge-base-en-v1.5) for semantic retrieval, and passed to GPT-4o to generate a **style archetype reading** — a literary, psychologically-informed portrait of the user's relationship to clothing.

### 2. Wardrobe Management

Users build a digital wardrobe by uploading photos of their actual garments. Each item is:

- Categorised (top, bottom, outerwear, shoes, bag, accessory)
- Analysed via GPT-4o vision for color, silhouette, fabric, and mood
- Stored with metadata for intelligent outfit composition

### 3. Daily Outfit Generation

Each day, users provide context:

- **Mood** — how they want to feel
- **Occasion** — work, date, creative time, errands, travel
- **Weather** — practical constraints
- **Focus item** — optionally select a specific piece to style around (from wardrobe or newly uploaded)

The system combines the user's style profile, full wardrobe inventory, daily context, and any uploaded item descriptions into a structured prompt. A fine-tuned GPT-4o-mini model generates an outfit suggestion in natural prose, referencing only items the user actually owns.

### 4. Feedback Loop

Users rate each suggestion (loved / neutral / not for me), building a preference signal for future refinement.

---

## Architecture

```
User Input
    │
    ├── Style Profile (structured JSON)
    │       │
    │       ├── BGE embedding (semantic vector)
    │       └── GPT-4o archetype generation
    │
    ├── Wardrobe (photos + metadata)
    │       │
    │       └── GPT-4o Vision (item analysis)
    │
    └── Daily Context (mood, occasion, weather, focus item)
            │
            └── Fine-tuned GPT-4o-mini (outfit suggestion)
                    │
                    └── Feedback collection (preference signal)
```

### Technical Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 6.0, Python 3.11 |
| Database | PostgreSQL (Neon) |
| LLM — Archetype & Vision | OpenAI GPT-4o |
| LLM — Outfit Generation | Fine-tuned GPT-4o-mini |
| Embeddings | sentence-transformers (BGE base) |
| Auth | django-allauth (invite-only access) |
| Deployment | Railway, Gunicorn, WhiteNoise |
| Frontend | Django templates, vanilla JS |

---

## Context Engineering

The core technical challenge is **context engineering** — structuring the right information in the right format so the model produces coherent, grounded outfit suggestions rather than generic fashion advice.

Key design decisions:

- **Structured wardrobe serialisation**: Each garment is passed as a JSON object with name, category, color, and style tags — enabling the model to reason about outfit composition as a constraint satisfaction problem.
- **Focus item enforcement**: When a user selects a specific item to style, the prompt architecture ensures it appears in the output and prevents category duplication (e.g., suggesting shoes when the focus item is already shoes).
- **Prose over lists**: The system prompt explicitly requests flowing text rather than bullet points or markdown, producing suggestions that read as personal advice rather than algorithmic output.
- **Profile-aware generation**: The full style profile (appearance, identity, lifestyle) is included in every suggestion call, allowing the model to maintain consistency with the user's stated preferences and constraints.

---

## Fine-Tuning

The outfit generation model is a fine-tuned GPT-4o-mini, trained on a custom dataset derived from:

- Personal outfit photographs annotated with detailed garment attributes (category, length, cut, silhouette, fabric, color, mood)
- Structured prompt-response pairs encoding the Oracle's voice, aesthetic judgment, and decision policy

The fine-tuning targets three capabilities:
1. **Aesthetic judgment** — understanding why certain combinations work
2. **Voice** — maintaining a consistent, literary tone
3. **Decision policy** — making grounded choices under real constraints (weather, occasion, wardrobe limitations)

---

## Running Locally

```bash
# Clone and set up
git clone https://github.com/eumiejhong/TheOracle.git
cd TheOracle
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Database
python manage.py migrate

# Run
python manage.py runserver
```

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for development |
| `DATABASE_URL` | PostgreSQL connection string |
| `OPENAI_API_KEY` | OpenAI API key |
| `INVITE_CODE` | Access code for new signups |

---

## Future Directions

- **Preference-aware retrieval**: Using the embedding layer to surface semantically similar past outfits and learn from feedback patterns
- **Multi-modal fine-tuning**: Training vision-language models on personal outfit data for direct image-to-suggestion pipelines
- **Temporal style modelling**: Tracking how a user's style evolves over time and adapting recommendations accordingly
- **Collaborative filtering**: Learning from style patterns across users with similar archetypes

---

## Author

Built by [Eumie Jhong](https://github.com/eumiejhong) — exploring the intersection of artificial intelligence, personal identity, and the philosophy of dress.
