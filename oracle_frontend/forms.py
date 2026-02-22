from django import forms
from allauth.account.forms import SignupForm
from django.conf import settings


class InviteSignupForm(SignupForm):
    invite_code = forms.CharField(
        label="Access Code",
        max_length=64,
        widget=forms.TextInput(attrs={"placeholder": "Enter your access code", "autocomplete": "off"})
    )

    def clean_invite_code(self):
        code = self.cleaned_data.get('invite_code', '').strip()
        if code != settings.INVITE_CODE:
            raise forms.ValidationError("Invalid access code.")
        return code

    def save(self, request):
        return super().save(request)


class BaseStyleProfileForm(forms.Form):

    # Appearance
    skin_tone = forms.ChoiceField(
        label="How would you describe your skin tone?",
        choices=[
            ("Fair or light", "Fair or light"),
            ("Medium or olive", "Medium or olive"),
            ("Deep or dark", "Deep or dark"),
            ("I'm not sure", "I'm not sure")
        ],
        widget=forms.RadioSelect
    )

    contrast_level = forms.ChoiceField(
        label="How would you describe the contrast between your features?",
        choices=[
            ("Low contrast", "Low contrast — light hair + fair skin"),
            ("Medium contrast", "Medium contrast — some difference, not sharp"),
            ("High contrast", "High contrast — dark hair + pale skin"),
            ("I'm not sure", "I'm not sure")
        ],
        widget=forms.RadioSelect
    )

    undertone = forms.ChoiceField(
        label="Do you lean warmer or cooler in tone?",
        choices=[
            ("Warm", "Warm — golden, peachy"),
            ("Cool", "Cool — pink, bluish"),
            ("Neutral", "Neutral — a bit of both"),
            ("I'm not sure", "I'm not sure")
        ],
        widget=forms.RadioSelect
    )

    # Style Preferences
    face_detail_preference = forms.ChoiceField(
        label="Do you prefer softer or more structured details near your face?",
        choices=[
            ("Soft", "Soft, round, or organic shapes"),
            ("Structured", "Structured, angular, or graphic lines"),
            ("Mix", "A mix — I go by outfit"),
            ("I'm not sure", "I'm not sure")
        ],
        widget=forms.RadioSelect
    )

    texture_notes = forms.CharField(
        label="What silhouettes or fabrics make you feel most like yourself?",
        widget=forms.Textarea(attrs={"placeholder": "e.g., Structured shoulders but soft drape, knits that skim but don't cling..."}),
        required=False
    )

    color_pref = forms.CharField(
        label="What are your favorite colors to wear?",
        widget=forms.Textarea(attrs={"placeholder": "e.g., Jewel tones, muted blue, baby pink..."}),
        required=False
    )

    style_constraints = forms.CharField(
        label="Anything you never wear?",
        widget=forms.Textarea(attrs={"placeholder": "e.g., Bodycon, loud prints, synthetics..."}),
        required=False
    )

    archetypes = forms.ChoiceField(
        label="Which style archetypes feel most like you?",
        choices=[
            ("Quiet Minimalism", "Quiet Minimalism"),
            ("Romantic Tailored", "Romantic Tailored"),
            ("Soft Sculptural", "Soft Sculptural"),
            ("90s Sharpness", "90s Sharpness"),
            ("Boyish Luxe", "Boyish Luxe"),
            ("Earthy Artisanal", "Earthy Artisanal"),
            ("Sleek + Functional", "Sleek + Functional"),
            ("I'm not sure", "I'm not sure")
        ],
        widget=forms.RadioSelect
    )

    aspirational_style = forms.CharField(
        label="Describe your style vision in your own words",
        widget=forms.Textarea(attrs={"placeholder": "e.g., A mix of sharp tailoring and soft romance..."}),
        required=False
    )

    # Lifestyle
    life_event = forms.CharField(
        label="Are you in a life transition?",
        widget=forms.Textarea(attrs={"placeholder": "e.g., Just moved, started a new role, navigating a breakup..."}),
        required=False
    )

    mobility = forms.ChoiceField(
        label="How do you usually move through your day?",
        choices=[
            ("I bike often", "I bike often"),
            ("I walk a lot", "I walk a lot"),
            ("I drive or use rideshare", "I drive or use rideshare"),
            ("I mostly stay home or work remotely", "I mostly stay home or work remotely"),
            ("I use mobility aids or need accessible styles", "I use mobility aids or need accessible styles"),
            ("My energy levels vary a lot day to day", "My energy levels vary a lot day to day")
        ],
        widget=forms.RadioSelect
    )

    climate_wear = forms.ChoiceField(
        label="What's the climate you usually dress for?",
        choices=[
            ("Warm year-round", "Warm year-round"),
            ("Mostly cold", "Mostly cold"),
            ("Transitional/layered seasons", "Transitional / layered seasons"),
            ("I travel between climates often", "I travel between climates often")
        ],
        widget=forms.RadioSelect
    )

    dress_formality = forms.ChoiceField(
        label="How formal is your day-to-day style?",
        choices=[
            ("Very casual", "Very casual"),
            ("Elevated casual", "Elevated casual"),
            ("Creative professional", "Creative professional"),
            ("Tailored / business", "Tailored / business")
        ],
        widget=forms.RadioSelect
    )

    wardrobe_phase = forms.ChoiceField(
        label="How would you describe your wardrobe right now?",
        choices=[
            ("Overflowing", "Overflowing — I need to refine"),
            ("Small but scattered", "Small but scattered — I need direction"),
            ("Building", "Building a new look from scratch"),
            ("Minimal", "Minimal — I love owning less")
        ],
        widget=forms.RadioSelect
    )

    shopping_behavior = forms.ChoiceField(
        label="How do you usually shop?",
        choices=[
            ("Mostly secondhand or vintage", "Mostly secondhand or vintage"),
            ("Investment pieces", "A few investment pieces each year"),
            ("Seasonal refresh", "I refresh seasonally"),
            ("Not buying", "Not buying — just want styling support")
        ],
        widget=forms.RadioSelect
    )

    budget_preference = forms.ChoiceField(
        label="What's your comfort zone for spending on a single item?",
        choices=[
            ("Under $50", "Under $50 — thrift or affordable"),
            ("$50-$150", "$50–$150 — mid-range and secondhand"),
            ("$150-$500", "$150–$500 — quality staples"),
            ("$500+", "$500+ — designer or archival"),
            ("Not buying", "Not buying right now")
        ],
        widget=forms.RadioSelect
    )


class DailyStyleInputForm(forms.Form):
    mood_today = forms.CharField(
        label="How do you want to feel today?",
        widget=forms.TextInput(attrs={"placeholder": "e.g., Confident but effortless, soft and protected..."})
    )

    occasion = forms.ChoiceField(
        label="What's the occasion?",
        choices=[
            ("Work day", "Work day"),
            ("Date or social event", "Date or social event"),
            ("Creative time", "Creative time"),
            ("Errands or casual day", "Errands or casual day"),
            ("Travel", "Travel"),
            ("Relaxing / staying in", "Relaxing / staying in"),
            ("Other", "Other")
        ],
        widget=forms.RadioSelect
    )

    weather = forms.ChoiceField(
        label="What's the weather like?",
        choices=[
            ("Cold and damp", "Cold and damp"),
            ("Cold and dry", "Cold and dry"),
            ("Warm and sunny", "Warm and sunny"),
            ("Hot and humid", "Hot and humid"),
            ("Transitional / layered weather", "Transitional / layered"),
            ("Unpredictable", "Unpredictable"),
            ("Not sure", "Not sure")
        ],
        widget=forms.RadioSelect
    )

    add_new_item = forms.ChoiceField(
        label="Are you styling a new item today?",
        choices=[("no", "No"), ("yes", "Yes")],
        widget=forms.RadioSelect,
        required=True
    )

    item_focus = forms.CharField(
        label="Is there a specific item you're trying to style?",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "e.g., My chocolate Lemaire trench..."})
    )

    image = forms.ImageField(
        label="Upload a photo of what you're styling",
        required=False
    )

    wardrobe_item = forms.ChoiceField(
        required=False,
        label="Or select from your wardrobe",
        choices=[],
    )

    def clean(self):
        cleaned_data = super().clean()
        add_new_item = cleaned_data.get("add_new_item")
        item_focus = cleaned_data.get("item_focus")
        image = cleaned_data.get("image")

        if add_new_item == "yes":
            if not item_focus or not image:
                raise forms.ValidationError(
                    "If you are styling a new item, both a description and image are required."
                )
        return cleaned_data


class WardrobeUploadForm(forms.Form):
    name = forms.CharField(
        label="Item name",
        widget=forms.TextInput(attrs={"placeholder": "e.g., White silk shirt"})
    )

    category = forms.ChoiceField(
        label="Category",
        choices=[
            ("Top", "Top"),
            ("Bottom", "Bottom"),
            ("Outerwear", "Outerwear"),
            ("Shoes", "Shoes"),
            ("Bag", "Bag"),
            ("Accessory", "Accessory")
        ]
    )

    image = forms.ImageField(
        label="Image",
        required=False
    )
