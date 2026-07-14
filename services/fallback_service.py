"""
Fallback service — generates prompt-specific, aesthetic website templates
when the OpenRouter API quota is exceeded or a runtime exception occurs.

KEY DESIGN: Every prompt produces a DIFFERENT website by extracting:
  - Business/person name from the prompt
  - Style keywords (colors, theme, mood)
  - Website type
  - Specific services/offerings mentioned
  - Language
"""

import re


# ─────────────────────────────────────────────
#  Language helpers
# ─────────────────────────────────────────────

def has_tamil(text: str) -> bool:
    return bool(re.search(r"[\u0B80-\u0BFF]", text))

def has_hindi(text: str) -> bool:
    return bool(re.search(r"[\u0900-\u097F]", text))


# ─────────────────────────────────────────────
#  Prompt content extractor
# ─────────────────────────────────────────────

def extract_prompt_content(prompt: str) -> dict:
    """
    Parse the user's prompt to extract:
    - business_name: any proper-noun name found
    - services: up to 3 specific items mentioned
    - tagline_hint: key adjectives for the tagline
    """
    prompt_lower = prompt.lower()

    # --- Extract a business / person name ---
    # Look for patterns like "for [Name]", "called [Name]", "named [Name]",
    # "[Name]'s", or a capitalised word sequence after "website for/of"
    name = None
    patterns = [
        r"(?:for|called|named|by)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})",
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})'s\s+website",
        r"website\s+(?:for|of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})",
        r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})\s+(?:restaurant|cafe|studio|shop|agency|group|tech|labs|solutions|co\b|inc\b|pvt)",
    ]
    for pat in patterns:
        m = re.search(pat, prompt)
        if m:
            name = m.group(1).strip()
            break

    # Fallback: take the longest capitalised word sequence in the prompt
    if not name:
        caps = re.findall(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*", prompt)
        if caps:
            name = max(caps, key=len)

    # --- Extract explicit service / item keywords ---
    # Look for comma-separated lists, "including X, Y and Z", etc.
    services_found = []
    list_match = re.findall(
        r"(?:include|with|has|featuring|offer(?:ing)?|section[s]?[:\s]+)\s+([a-zA-Z ,&]+?)(?:\.|,|$|\n)",
        prompt_lower
    )
    for chunk in list_match:
        for part in re.split(r",|and|&", chunk):
            part = part.strip()
            if 3 < len(part) < 30:
                services_found.append(part.title())
    services_found = list(dict.fromkeys(services_found))[:3]  # deduplicate, max 3

    # --- Extract style adjectives ---
    style_words = []
    for word in ["modern", "minimalist", "elegant", "bold", "vibrant", "luxury",
                 "clean", "dark", "light", "colorful", "playful", "professional",
                 "creative", "classic", "futuristic", "warm", "cool"]:
        if word in prompt_lower:
            style_words.append(word)

    return {
        "name": name or "Your Brand",
        "services": services_found,
        "style_words": style_words,
    }


# ─────────────────────────────────────────────
#  Main entry point
# ─────────────────────────────────────────────

def generate_fallback_website(prompt: str) -> dict:
    """
    Generate a prompt-specific rule-based website.
    Every different prompt produces visually different output:
      - Different business name
      - Different color palette
      - Different copy / services
      - Different hero headline
    """
    prompt_lower = prompt.lower()

    # 1. Language
    if has_tamil(prompt):
        lang_name, lang_code = "Tamil", "ta"
    elif has_hindi(prompt):
        lang_name, lang_code = "Hindi", "hi"
    else:
        lang_name, lang_code = "English", "en"

    # 2. Website type
    if any(k in prompt_lower for k in [
        "portfolio", "cv", "resume", "developer", "photographer",
        "designer", "profile", "about me", "freelancer", "artist", "writer"
    ]):
        web_type = "portfolio"
    elif any(k in prompt_lower for k in [
        "restaurant", "cafe", "food", "bakery", "menu", "dining",
        "chef", "eat", "bistro", "coffee", "tea", "pizza", "burger",
        "sushi", "indian", "italian", "chinese", "thai", "spice"
    ]):
        web_type = "restaurant"
    elif any(k in prompt_lower for k in [
        "business", "company", "agency", "consulting", "startup",
        "corporate", "service", "saas", "tech", "marketing",
        "finance", "firm", "solutions", "labs", "studio", "group"
    ]):
        web_type = "business"
    else:
        web_type = "landing page"

    # 3. Theme
    is_light = "light" in prompt_lower or "white" in prompt_lower or "bright" in prompt_lower
    if is_light:
        bg_color, card_bg = "#f8fafc", "#ffffff"
        text_color, text_muted = "#0f172a", "#64748b"
        border_color = "#e2e8f0"
    else:
        bg_color, card_bg = "#0b0f19", "#151d30"
        text_color, text_muted = "#f8fafc", "#94a3b8"
        border_color = "#1e293b"

    # 4. Accent colour — detected from prompt keywords
    accent_map = [
        (["gold", "yellow", "amber", "warm"],       "#fbbf24", "#d97706", "gold"),
        (["green", "emerald", "nature", "eco"],     "#10b981", "#059669", "emerald"),
        (["red", "rose", "crimson", "passion"],     "#f43f5e", "#e11d48", "red"),
        (["purple", "violet", "luxury"],            "#a855f7", "#9333ea", "purple"),
        (["orange", "spice", "energy"],             "#f97316", "#ea580c", "orange"),
        (["teal", "cyan", "aqua", "ocean"],         "#14b8a6", "#0d9488", "teal"),
        (["blue", "sky", "ocean", "corporate"],     "#3b82f6", "#2563eb", "blue"),
        (["pink", "blush", "beauty", "salon"],      "#ec4899", "#db2777", "pink"),
    ]
    accent_color, accent_hover, accent_name = "#6366f1", "#4f46e5", "indigo"
    for keys, color, hover, name in accent_map:
        if any(k in prompt_lower for k in keys):
            accent_color, accent_hover, accent_name = color, hover, name
            break

    # 5. Extract prompt-specific content
    extracted = extract_prompt_content(prompt)
    biz_name = extracted["name"]
    extra_services = extracted["services"]
    style_words = extracted["style_words"]
    style_desc = ", ".join(style_words) if style_words else "modern"

    # 6. Build prompt-specific content
    content = build_prompt_content(
        web_type, lang_code, prompt, biz_name, extra_services, accent_name, style_desc
    )

    # 7. Generate code
    html_body = generate_html_body(web_type, content, lang_code, accent_color, prompt)
    css_code  = generate_css_code(bg_color, card_bg, text_color, text_muted,
                                   border_color, accent_color, accent_hover, is_light)
    js_code   = generate_js_code(content["submit_message"])

    # 8. Requirements and plan
    requirements = {
        "website_type": web_type,
        "business_category": web_type if web_type != "landing page" else "general",
        "target_audience": "General public",
        "pages": ["Home"],
        "sections": ["hero", "about", "services", "contact", "footer"],
        "color_scheme": f"{'Light' if is_light else 'Dark'} theme with {accent_name} accent",
        "primary_color": bg_color,
        "secondary_color": accent_color,
        "style": style_desc or "modern",
        "tone": "elegant",
        "features": ["responsive design", "contact form", "interactive animations"],
        "content_summary": f"{style_desc.title()} {web_type} website for {biz_name}.",
    }

    plan = {
        "title": content["site_title"],
        "tagline": content["hero_subtitle"],
        "navigation": [
            content["nav_home"], content["nav_about"],
            content["nav_services"], content["nav_contact"],
        ],
        "sections": [
            {"id": "hero",     "type": "hero",     "title": content["hero_title"],     "layout": "split"},
            {"id": "about",    "type": "about",    "title": content["about_title"],    "layout": "two-column"},
            {"id": "services", "type": "services", "title": content["services_title"], "layout": "grid"},
            {"id": "contact",  "type": "contact",  "title": content["contact_title"],  "layout": "centered"},
            {"id": "footer",   "type": "footer",   "title": "Footer",                  "layout": "footer"},
        ],
        "color_palette": {
            "primary": bg_color, "secondary": card_bg,
            "accent": accent_color, "background": bg_color, "text": text_color,
        },
        "fonts": {"heading": "Outfit", "body": "Inter"},
    }

    return {
        "detected_language": lang_name,
        "requirements": requirements,
        "plan": plan,
        "html": html_body,
        "css": css_code,
        "js": js_code,
        "website_type": web_type,
    }


# ─────────────────────────────────────────────
#  Prompt-specific content builder
# ─────────────────────────────────────────────

def build_prompt_content(web_type, lang_code, prompt, biz_name, extra_services,
                          accent_name, style_desc) -> dict:
    """
    Compose all copy text from the prompt's extracted details so each prompt
    yields genuinely different page text.
    """
    prompt_lower = prompt.lower()

    # ── shared nav labels (lang-aware) ──────────────────────────────────────
    if lang_code == "ta":
        nav = {"home": "முகப்பு", "about": "பற்றி", "services": "சேவைகள்", "contact": "தொடர்பு"}
        copyright_text = "அனைத்து உரிமைகளும் பாதுகாக்கப்பட்டவை."
    elif lang_code == "hi":
        nav = {"home": "होम", "about": "परिचय", "services": "सेवाएं", "contact": "संपर्क"}
        copyright_text = "सर्वाधिकार सुरक्षित।"
    else:
        nav = {"home": "Home", "about": "About", "services": "Services", "contact": "Contact"}
        copyright_text = "All rights reserved."

    # ── restaurant ──────────────────────────────────────────────────────────
    if web_type == "restaurant":
        # Derive cuisine type from prompt
        cuisines = {
            "indian": "Authentic Indian", "italian": "Italian", "chinese": "Chinese",
            "thai": "Thai", "mexican": "Mexican", "japanese": "Japanese",
            "french": "French", "greek": "Greek", "mediterranean": "Mediterranean",
            "american": "American", "sushi": "Japanese", "pizza": "Italian",
            "burger": "American Grill", "spice": "Spiced Asian",
            "coffee": "Café & Bakery", "cafe": "Café & Bistro",
        }
        cuisine = "Fine Dining"
        for k, v in cuisines.items():
            if k in prompt_lower:
                cuisine = v
                break

        menu_items = extra_services if extra_services else [
            f"{cuisine} Chef's Special", "Signature Dessert", "House Cocktail"
        ]
        while len(menu_items) < 3:
            menu_items.append(f"{cuisine} Seasonal Dish")

        return {
            "site_title": f"{biz_name} | {cuisine} Restaurant",
            "nav_home": nav["home"], "nav_about": "Our Story",
            "nav_services": "Menu", "nav_contact": "Reservations",
            "hero_title": f"Taste the Essence of {cuisine} Cuisine",
            "hero_subtitle": (
                f"At {biz_name}, every dish is crafted with passion, "
                f"fresh ingredients, and {style_desc} presentation. "
                "Dine with us for an unforgettable experience."
            ),
            "hero_cta": "Explore Our Menu",
            "about_title": "Our Culinary Story",
            "about_desc": (
                f"{biz_name} was founded by passionate chefs who believe great food "
                f"should be both beautiful and delicious. Our {style_desc} kitchen "
                "sources the finest local and seasonal produce to bring you "
                f"authentic {cuisine} flavours with a contemporary twist."
            ),
            "skills_title": "Our Standards",
            "services_title": "Chef's Recommendations",
            "service1_title": menu_items[0],
            "service1_desc": f"A signature {cuisine} masterpiece — prepared fresh daily by our head chef.",
            "service2_title": menu_items[1],
            "service2_desc": f"A timeless favourite elevated with premium {cuisine} ingredients.",
            "service3_title": menu_items[2],
            "service3_desc": f"Our chef's personal creation — a must-try at {biz_name}.",
            "contact_title": "Reserve Your Table",
            "contact_subtitle": f"Book your dining experience at {biz_name} today.",
            "btn_submit": "Book Table",
            "submit_message": f"Reservation confirmed! We look forward to welcoming you to {biz_name}.",
            "copyright": copyright_text,
        }

    # ── portfolio ────────────────────────────────────────────────────────────
    elif web_type == "portfolio":
        roles = {
            "developer": "Full-Stack Developer", "designer": "UI/UX Designer",
            "photographer": "Photographer", "writer": "Content Writer",
            "artist": "Digital Artist", "engineer": "Software Engineer",
            "animator": "Motion Designer", "filmmaker": "Filmmaker",
            "architect": "Architect", "data": "Data Scientist",
        }
        role = "Creative Professional"
        for k, v in roles.items():
            if k in prompt_lower:
                role = v
                break

        skills = extra_services if extra_services else [
            "UI / UX Design", "Full-Stack Development", "Brand Strategy"
        ]
        while len(skills) < 3:
            skills.append("Creative Problem Solving")

        return {
            "site_title": f"{biz_name} | {role}",
            "nav_home": nav["home"], "nav_about": nav["about"],
            "nav_services": "Work", "nav_contact": nav["contact"],
            "hero_title": f"Hi, I'm {biz_name} — {role}",
            "hero_subtitle": (
                f"I create {style_desc} digital experiences that are beautiful, "
                "functional, and built to perform. Let's build something great together."
            ),
            "hero_cta": "View My Work",
            "about_title": f"About {biz_name}",
            "about_desc": (
                f"I'm a passionate {role} with a love for {style_desc} design and "
                "clean code. Over the years I've partnered with startups, agencies, "
                "and enterprise clients to bring their vision to life through "
                "thoughtful, pixel-perfect execution."
            ),
            "skills_title": "Core Skills",
            "services_title": "What I Do",
            "service1_title": skills[0],
            "service1_desc": f"Expert {skills[0]} tailored to your brand's personality and goals.",
            "service2_title": skills[1],
            "service2_desc": f"Scalable, maintainable {skills[1]} solutions built with best practices.",
            "service3_title": skills[2],
            "service3_desc": f"End-to-end {skills[2]} that sets you apart from the competition.",
            "contact_title": "Let's Work Together",
            "contact_subtitle": f"Have a project for me? I'd love to hear from you.",
            "btn_submit": "Send Message",
            "submit_message": f"Thanks! I'll get back to you shortly. — {biz_name}",
            "copyright": copyright_text,
        }

    # ── business ─────────────────────────────────────────────────────────────
    elif web_type == "business":
        industries = {
            "tech": "Technology", "marketing": "Digital Marketing",
            "finance": "Financial Services", "legal": "Legal Services",
            "consulting": "Consulting", "agency": "Creative Agency",
            "real estate": "Real Estate", "healthcare": "Healthcare",
            "education": "EdTech", "logistics": "Logistics",
            "insurance": "Insurance", "hr": "HR Solutions",
        }
        industry = "Business Solutions"
        for k, v in industries.items():
            if k in prompt_lower:
                industry = v
                break

        offerings = extra_services if extra_services else [
            "Strategic Advisory", "Digital Transformation", "Growth Analytics"
        ]
        while len(offerings) < 3:
            offerings.append("Custom Business Solutions")

        return {
            "site_title": f"{biz_name} | {industry}",
            "nav_home": nav["home"], "nav_about": "About Us",
            "nav_services": "Services", "nav_contact": "Get Started",
            "hero_title": f"Elevate Your Business with {biz_name}",
            "hero_subtitle": (
                f"{biz_name} delivers {style_desc} {industry.lower()} solutions "
                "that drive measurable growth, streamline operations, "
                "and position your brand for sustainable success."
            ),
            "hero_cta": "Get Free Consultation",
            "about_title": f"Who is {biz_name}?",
            "about_desc": (
                f"{biz_name} is a leading {industry} firm trusted by hundreds of "
                f"businesses worldwide. Our {style_desc} approach combines deep "
                "industry expertise with cutting-edge technology to deliver "
                "results that consistently exceed client expectations."
            ),
            "skills_title": "Our Capabilities",
            "services_title": "Our Core Services",
            "service1_title": offerings[0],
            "service1_desc": f"Comprehensive {offerings[0].lower()} tailored to your unique business challenges.",
            "service2_title": offerings[1],
            "service2_desc": f"End-to-end {offerings[1].lower()} powered by the latest tools and frameworks.",
            "service3_title": offerings[2],
            "service3_desc": f"Proven {offerings[2].lower()} methodologies that deliver consistent ROI.",
            "contact_title": "Start a Conversation",
            "contact_subtitle": f"Tell us about your goals and let {biz_name} build the path forward.",
            "btn_submit": "Submit Request",
            "submit_message": f"Request received! A {biz_name} consultant will reach out within 24 hours.",
            "copyright": copyright_text,
        }

    # ── landing page ─────────────────────────────────────────────────────────
    else:
        product_hints = {
            "app": "App", "tool": "Tool", "platform": "Platform",
            "saas": "SaaS", "software": "Software", "service": "Service",
            "store": "Store", "shop": "Shop", "product": "Product",
        }
        product_type = "Solution"
        for k, v in product_hints.items():
            if k in prompt_lower:
                product_type = v
                break

        features = extra_services if extra_services else [
            "Lightning-Fast Performance", "Enterprise-Grade Security", "Seamless Integrations"
        ]
        while len(features) < 3:
            features.append("24/7 Support")

        return {
            "site_title": f"{biz_name} | {style_desc.title()} {product_type}",
            "nav_home": nav["home"], "nav_about": "Features",
            "nav_services": "Pricing", "nav_contact": nav["contact"],
            "hero_title": f"The {style_desc.title()} {product_type} Built for You",
            "hero_subtitle": (
                f"{biz_name} is the {style_desc} {product_type.lower()} that "
                "simplifies your workflow, amplifies your productivity, "
                "and helps your team achieve more — every single day."
            ),
            "hero_cta": "Get Started Free",
            "about_title": f"Why {biz_name}?",
            "about_desc": (
                f"{biz_name} was designed from the ground up to be the most "
                f"{style_desc} and effective {product_type.lower()} in its class. "
                "Our team of engineers and designers obsess over every detail "
                "so you don't have to — just launch and grow."
            ),
            "skills_title": "Key Benefits",
            "services_title": "Core Features",
            "service1_title": features[0],
            "service1_desc": f"Experience {features[0].lower()} that sets {biz_name} apart from every competitor.",
            "service2_title": features[1],
            "service2_desc": f"Built-in {features[1].lower()} — your data and users are always protected.",
            "service3_title": features[2],
            "service3_desc": f"Native {features[2].lower()} so {biz_name} fits perfectly into your existing stack.",
            "contact_title": "Stay in the Loop",
            "contact_subtitle": f"Join thousands of teams already using {biz_name}.",
            "btn_submit": "Subscribe",
            "submit_message": f"Welcome aboard! You're now part of the {biz_name} community.",
            "copyright": copyright_text,
        }


# ─────────────────────────────────────────────
#  HTML Body
# ─────────────────────────────────────────────

def generate_html_body(web_type: str, content: dict, lang_code: str,
                        accent_color: str, prompt: str = "") -> str:
    """Build the HTML layout body with custom copy."""
    about_extra_html = ""
    services_extra_html = ""

    if web_type == "portfolio":
        about_extra_html = f"""
        <div class="skills-card">
            <h3>{content['skills_title']}</h3>
            <div class="skill-bar-container">
                <div class="skill-label"><span>{content['service1_title']}</span><span>95%</span></div>
                <div class="skill-progress"><div class="skill-fill" style="width: 95%"></div></div>
            </div>
            <div class="skill-bar-container">
                <div class="skill-label"><span>{content['service2_title']}</span><span>90%</span></div>
                <div class="skill-progress"><div class="skill-fill" style="width: 90%"></div></div>
            </div>
            <div class="skill-bar-container">
                <div class="skill-label"><span>{content['service3_title']}</span><span>85%</span></div>
                <div class="skill-progress"><div class="skill-fill" style="width: 85%"></div></div>
            </div>
        </div>
        """
        services_extra_html = f"""
        <div class="service-card">
            <div class="service-icon"><i class="fas fa-palette"></i></div>
            <h3>{content['service1_title']}</h3>
            <p>{content['service1_desc']}</p>
        </div>
        <div class="service-card">
            <div class="service-icon"><i class="fas fa-code"></i></div>
            <h3>{content['service2_title']}</h3>
            <p>{content['service2_desc']}</p>
        </div>
        <div class="service-card">
            <div class="service-icon"><i class="fas fa-bullseye"></i></div>
            <h3>{content['service3_title']}</h3>
            <p>{content['service3_desc']}</p>
        </div>
        """

    elif web_type == "restaurant":
        about_extra_html = f"""
        <div class="skills-card">
            <h3>{content['skills_title']}</h3>
            <ul class="standards-list" style="list-style:none;padding:0;margin:0">
                <li style="margin-bottom:1rem;display:flex;align-items:center;gap:0.75rem">
                    <i class="fas fa-check-circle" style="color:{accent_color}"></i>
                    100% Fresh &amp; Locally-Sourced Ingredients
                </li>
                <li style="margin-bottom:1rem;display:flex;align-items:center;gap:0.75rem">
                    <i class="fas fa-check-circle" style="color:{accent_color}"></i>
                    Award-Winning Hospitality &amp; Service
                </li>
                <li style="margin-bottom:1rem;display:flex;align-items:center;gap:0.75rem">
                    <i class="fas fa-check-circle" style="color:{accent_color}"></i>
                    Seasonal &amp; Chef-Curated Menu
                </li>
            </ul>
        </div>
        """
        services_extra_html = f"""
        <div class="service-card">
            <div class="service-icon"><i class="fas fa-utensils"></i></div>
            <h3>{content['service1_title']}</h3>
            <p>{content['service1_desc']}</p>
            <div class="price-tag" style="margin-top:1rem;font-weight:700;color:{accent_color};font-size:1.25rem">$18.99</div>
        </div>
        <div class="service-card">
            <div class="service-icon"><i class="fas fa-fire"></i></div>
            <h3>{content['service2_title']}</h3>
            <p>{content['service2_desc']}</p>
            <div class="price-tag" style="margin-top:1rem;font-weight:700;color:{accent_color};font-size:1.25rem">$24.50</div>
        </div>
        <div class="service-card">
            <div class="service-icon"><i class="fas fa-cookie-bite"></i></div>
            <h3>{content['service3_title']}</h3>
            <p>{content['service3_desc']}</p>
            <div class="price-tag" style="margin-top:1rem;font-weight:700;color:{accent_color};font-size:1.25rem">$9.00</div>
        </div>
        """

    elif web_type == "business":
        about_extra_html = f"""
        <div class="skills-card">
            <h3>{content['skills_title']}</h3>
            <div class="skill-bar-container">
                <div class="skill-label"><span>{content['service1_title']}</span><span>98%</span></div>
                <div class="skill-progress"><div class="skill-fill" style="width: 98%"></div></div>
            </div>
            <div class="skill-bar-container">
                <div class="skill-label"><span>{content['service2_title']}</span><span>94%</span></div>
                <div class="skill-progress"><div class="skill-fill" style="width: 94%"></div></div>
            </div>
            <div class="skill-bar-container">
                <div class="skill-label"><span>{content['service3_title']}</span><span>90%</span></div>
                <div class="skill-progress"><div class="skill-fill" style="width: 90%"></div></div>
            </div>
        </div>
        """
        services_extra_html = f"""
        <div class="service-card">
            <div class="service-icon"><i class="fas fa-chart-line"></i></div>
            <h3>{content['service1_title']}</h3>
            <p>{content['service1_desc']}</p>
        </div>
        <div class="service-card">
            <div class="service-icon"><i class="fas fa-sync-alt"></i></div>
            <h3>{content['service2_title']}</h3>
            <p>{content['service2_desc']}</p>
        </div>
        <div class="service-card">
            <div class="service-icon"><i class="fas fa-wallet"></i></div>
            <h3>{content['service3_title']}</h3>
            <p>{content['service3_desc']}</p>
        </div>
        """

    else:  # landing page
        about_extra_html = f"""
        <div class="skills-card">
            <h3>{content['skills_title']}</h3>
            <ul class="standards-list" style="list-style:none;padding:0;margin:0">
                <li style="margin-bottom:1rem;display:flex;align-items:center;gap:0.75rem">
                    <i class="fas fa-arrow-alt-circle-right" style="color:{accent_color}"></i>
                    Boost Team Efficiency by 30%+
                </li>
                <li style="margin-bottom:1rem;display:flex;align-items:center;gap:0.75rem">
                    <i class="fas fa-arrow-alt-circle-right" style="color:{accent_color}"></i>
                    Zero-Downtime Cloud Infrastructure
                </li>
                <li style="margin-bottom:1rem;display:flex;align-items:center;gap:0.75rem">
                    <i class="fas fa-arrow-alt-circle-right" style="color:{accent_color}"></i>
                    Dedicated 24/7 Enterprise Support
                </li>
            </ul>
        </div>
        """
        services_extra_html = f"""
        <div class="service-card">
            <div class="service-icon"><i class="fas fa-bolt"></i></div>
            <h3>{content['service1_title']}</h3>
            <p>{content['service1_desc']}</p>
        </div>
        <div class="service-card">
            <div class="service-icon"><i class="fas fa-shield-alt"></i></div>
            <h3>{content['service2_title']}</h3>
            <p>{content['service2_desc']}</p>
        </div>
        <div class="service-card">
            <div class="service-icon"><i class="fas fa-cloud-upload-alt"></i></div>
            <h3>{content['service3_title']}</h3>
            <p>{content['service3_desc']}</p>
        </div>
        """

    return f"""
    <!-- API Fallback Notice Banner -->
    <div class="api-fallback-banner">
        <span><i class="fas fa-info-circle"></i> <strong>Offline Mode:</strong>
        Your API quota is currently exhausted. This is a fully customised template
        Your API quota is currently exhausted. This is a fully customised template
        based on your prompt — update your OpenRouter API key to get AI-generated results.</span>
    </div>

    <!-- Navigation -->
    <nav class="navbar" id="navbar">
        <div class="nav-container">
            <div class="nav-brand">
                <span class="brand-icon"><i class="fas fa-globe"></i></span>
                <span class="brand-name">{content['site_title'].split('|')[0].strip()}</span>
            </div>
            <ul class="nav-links" id="nav-menu">
                <li><a href="#hero">{content['nav_home']}</a></li>
                <li><a href="#about">{content['nav_about']}</a></li>
                <li><a href="#services">{content['nav_services']}</a></li>
                <li><a href="#contact">{content['nav_contact']}</a></li>
            </ul>
            <button class="hamburger" id="menu-hamburger" aria-label="Menu">
                <i class="fas fa-bars"></i>
            </button>
        </div>
    </nav>

    <!-- Hero -->
    <section class="hero-section" id="hero">
        <div class="hero-content">
            <div class="hero-badge"><i class="fas fa-star"></i> Premium Quality</div>
            <h1 class="hero-title">{content['hero_title']}</h1>
            <p class="hero-subtitle">{content['hero_subtitle']}</p>
            <div class="hero-actions">
                <a href="#contact" class="btn-primary-hero">{content['hero_cta']}</a>
                <a href="#about" class="btn-ghost-hero">Learn More <i class="fas fa-arrow-right"></i></a>
            </div>
        </div>
        <div class="hero-visual">
            <div class="hero-card floating">
                <div class="hero-card-inner">
                    <i class="fas fa-magic" style="font-size:3rem;margin-bottom:1rem"></i>
                    <p style="font-weight:600;margin:0">{content['site_title'].split('|')[0].strip()}</p>
                    <p style="font-size:.85rem;opacity:.7;margin:.25rem 0 0">{content['nav_services']}</p>
                </div>
            </div>
        </div>
    </section>

    <!-- About -->
    <section class="about-section" id="about">
        <div class="section-container">
            <div class="about-grid">
                <div class="about-text">
                    <div class="section-tag">{content['nav_about']}</div>
                    <h2 class="section-title">{content['about_title']}</h2>
                    <p class="section-desc">{content['about_desc']}</p>
                </div>
                <div class="about-extras">
                    {about_extra_html}
                </div>
            </div>
        </div>
    </section>

    <!-- Services -->
    <section class="services-section" id="services">
        <div class="section-container">
            <div class="section-header">
                <div class="section-tag">{content['nav_services']}</div>
                <h2 class="section-title">{content['services_title']}</h2>
            </div>
            <div class="services-grid">
                {services_extra_html}
            </div>
        </div>
    </section>

    <!-- Contact -->
    <section class="contact-section" id="contact">
        <div class="section-container">
            <div class="section-header">
                <div class="section-tag">{content['nav_contact']}</div>
                <h2 class="section-title">{content['contact_title']}</h2>
                <p class="section-desc">{content['contact_subtitle']}</p>
            </div>
            <form class="contact-form" id="simulated-contact-form">
                <div class="form-row">
                    <input type="text" class="form-input" placeholder="Your Name" required>
                    <input type="email" class="form-input" placeholder="Your Email" required>
                </div>
                <input type="text" class="form-input" placeholder="Subject">
                <textarea class="form-input form-textarea" placeholder="Your message..." rows="5" required></textarea>
                <button type="submit" class="btn-primary-hero" style="width:100%;justify-content:center">
                    <i class="fas fa-paper-plane"></i> {content['btn_submit']}
                </button>
            </form>
        </div>
    </section>

    <!-- Footer -->
    <footer class="footer-section">
        <div class="footer-inner">
            <div class="footer-brand">
                <span class="brand-name">{content['site_title'].split('|')[0].strip()}</span>
            </div>
            <p class="footer-copy">&copy; 2025 {content['site_title'].split('|')[0].strip()}. {content['copyright']}</p>
        </div>
    </footer>
"""


# ─────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────

def generate_css_code(bg_color, card_bg, text_color, text_muted, border_color,
                       accent_color, accent_hover, is_light) -> str:
    return f"""
/* ── Reset & Base ── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
:root {{
  --bg: {bg_color};
  --card: {card_bg};
  --text: {text_color};
  --muted: {text_muted};
  --border: {border_color};
  --accent: {accent_color};
  --accent-hover: {accent_hover};
  --radius: 12px;
  --shadow: 0 4px 24px rgba(0,0,0,{'.08' if is_light else '.4'});
}}
html {{ scroll-behavior: smooth; }}
body {{
  font-family: 'Inter', system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.7;
  overflow-x: hidden;
}}
a {{ color: inherit; text-decoration: none; }}
img {{ max-width: 100%; display: block; }}

/* ── Fallback Banner ── */
.api-fallback-banner {{
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-hover) 100%);
  color: #fff;
  text-align: center;
  padding: .75rem 1.5rem;
  font-size: .85rem;
  font-weight: 500;
  position: relative;
  z-index: 1000;
}}
.api-fallback-banner i {{ margin-right: .4rem; }}

/* ── Navbar ── */
.navbar {{
  position: sticky;
  top: 0;
  z-index: 900;
  background: {'rgba(248,250,252,0.92)' if is_light else 'rgba(11,15,25,0.92)'};
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
}}
.nav-container {{
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}}
.nav-brand {{ display: flex; align-items: center; gap: .6rem; font-weight: 700; font-size: 1.1rem; }}
.brand-icon {{ width: 32px; height: 32px; background: var(--accent); border-radius: 8px;
               display: flex; align-items: center; justify-content: center; color: #fff; font-size: .8rem; }}
.nav-links {{ list-style: none; display: flex; gap: 2rem; }}
.nav-links a {{ font-size: .9rem; font-weight: 500; color: var(--muted); transition: color .2s; }}
.nav-links a:hover {{ color: var(--accent); }}
.hamburger {{ display: none; background: none; border: none; cursor: pointer;
              font-size: 1.2rem; color: var(--text); }}

/* ── Hero ── */
.hero-section {{
  min-height: 92vh;
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: center;
  gap: 4rem;
  max-width: 1200px;
  margin: 0 auto;
  padding: 5rem 2rem;
}}
.hero-badge {{
  display: inline-flex; align-items: center; gap: .4rem;
  background: {'rgba(99,102,241,.1)' if is_light else 'rgba(99,102,241,.15)'};
  color: var(--accent);
  padding: .35rem .9rem;
  border-radius: 50px;
  font-size: .8rem; font-weight: 600;
  margin-bottom: 1.5rem;
  border: 1px solid {'rgba(99,102,241,.2)' if is_light else 'rgba(99,102,241,.3)'};
}}
.hero-title {{
  font-family: 'Outfit', sans-serif;
  font-size: clamp(2.2rem, 5vw, 3.8rem);
  font-weight: 800;
  line-height: 1.15;
  margin-bottom: 1.5rem;
  background: linear-gradient(135deg, var(--text) 0%, var(--accent) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}}
.hero-subtitle {{
  font-size: 1.1rem; color: var(--muted);
  max-width: 520px; margin-bottom: 2.5rem; line-height: 1.8;
}}
.hero-actions {{ display: flex; gap: 1rem; flex-wrap: wrap; align-items: center; }}
.btn-primary-hero {{
  display: inline-flex; align-items: center; gap: .5rem;
  background: var(--accent); color: #fff;
  padding: .85rem 2rem; border-radius: var(--radius);
  font-weight: 600; font-size: .95rem;
  transition: all .25s; border: none; cursor: pointer;
}}
.btn-primary-hero:hover {{ background: var(--accent-hover); transform: translateY(-2px); box-shadow: 0 8px 24px color-mix(in srgb, var(--accent) 40%, transparent); }}
.btn-ghost-hero {{
  display: inline-flex; align-items: center; gap: .5rem;
  color: var(--muted); font-weight: 500; font-size: .95rem;
  transition: color .2s;
}}
.btn-ghost-hero:hover {{ color: var(--text); }}
.hero-visual {{
  display: flex; align-items: center; justify-content: center;
}}
.hero-card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 24px;
  padding: 3rem;
  text-align: center;
  box-shadow: var(--shadow);
  width: 100%; max-width: 360px;
}}
.hero-card-inner i {{ color: var(--accent); }}
.floating {{ animation: float 4s ease-in-out infinite; }}
@keyframes float {{ 0%,100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-16px); }} }}

/* ── Sections ── */
.section-container {{ max-width: 1200px; margin: 0 auto; padding: 6rem 2rem; }}
.section-header {{ text-align: center; margin-bottom: 3.5rem; }}
.section-tag {{
  display: inline-block;
  background: {'rgba(99,102,241,.08)' if is_light else 'rgba(99,102,241,.12)'};
  color: var(--accent);
  padding: .3rem .85rem; border-radius: 50px;
  font-size: .8rem; font-weight: 600; letter-spacing: .5px;
  text-transform: uppercase; margin-bottom: 1rem;
}}
.section-title {{
  font-family: 'Outfit', sans-serif;
  font-size: clamp(1.8rem, 3.5vw, 2.8rem);
  font-weight: 700; margin-bottom: .75rem;
}}
.section-desc {{ color: var(--muted); max-width: 580px; margin: 0 auto; }}

/* ── About ── */
.about-section {{ background: {'#f1f5f9' if is_light else '#0d1321'}; }}
.about-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4rem; align-items: center; }}
.about-text .section-tag {{ display: inline-block; margin-bottom: 1rem; }}
.about-text .section-title {{ text-align: left; }}
.about-text .section-desc {{ text-align: left; max-width: none; }}
.skills-card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 2rem;
  box-shadow: var(--shadow);
}}
.skills-card h3 {{ font-size: 1rem; font-weight: 700; margin-bottom: 1.5rem; }}
.skill-bar-container {{ margin-bottom: 1.25rem; }}
.skill-label {{ display: flex; justify-content: space-between; font-size: .85rem; margin-bottom: .4rem; color: var(--muted); }}
.skill-progress {{ background: var(--border); border-radius: 50px; height: 7px; }}
.skill-fill {{ height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent-hover)); border-radius: 50px; animation: growBar 1.2s ease; }}
@keyframes growBar {{ from {{ width: 0 !important; }} }}

/* ── Services ── */
.services-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem; }}
.service-card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 2rem;
  transition: transform .25s, box-shadow .25s, border-color .25s;
  box-shadow: var(--shadow);
}}
.service-card:hover {{
  transform: translateY(-6px);
  border-color: var(--accent);
  box-shadow: 0 16px 40px color-mix(in srgb, var(--accent) 20%, transparent);
}}
.service-icon {{
  width: 52px; height: 52px;
  background: linear-gradient(135deg, var(--accent), var(--accent-hover));
  border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 1.2rem;
  margin-bottom: 1.25rem;
}}
.service-card h3 {{ font-size: 1.05rem; font-weight: 700; margin-bottom: .6rem; }}
.service-card p {{ color: var(--muted); font-size: .92rem; line-height: 1.7; }}

/* ── Contact ── */
.contact-section {{ background: {'#f1f5f9' if is_light else '#0d1321'}; }}
.contact-form {{
  max-width: 640px; margin: 0 auto;
  display: flex; flex-direction: column; gap: 1rem;
}}
.form-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
.form-input {{
  width: 100%;
  background: var(--card);
  border: 1.5px solid var(--border);
  border-radius: var(--radius);
  padding: .85rem 1.1rem;
  color: var(--text);
  font-size: .95rem;
  font-family: inherit;
  transition: border-color .2s, box-shadow .2s;
  outline: none;
}}
.form-input:focus {{ border-color: var(--accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 15%, transparent); }}
.form-input::placeholder {{ color: var(--muted); }}
.form-textarea {{ resize: vertical; min-height: 120px; }}

/* ── Footer ── */
.footer-section {{
  border-top: 1px solid var(--border);
  padding: 2.5rem 2rem;
  text-align: center;
}}
.footer-inner {{ max-width: 1200px; margin: 0 auto; }}
.footer-brand {{ margin-bottom: .75rem; font-weight: 700; font-size: 1.1rem; }}
.footer-copy {{ color: var(--muted); font-size: .85rem; }}

/* ── Mobile ── */
@media (max-width: 768px) {{
  .hero-section {{ grid-template-columns: 1fr; padding: 3rem 1.5rem; min-height: auto; }}
  .hero-visual {{ display: none; }}
  .about-grid {{ grid-template-columns: 1fr; }}
  .form-row {{ grid-template-columns: 1fr; }}
  .nav-links {{ display: none; position: fixed; inset: 0; background: var(--bg);
                flex-direction: column; align-items: center; justify-content: center;
                gap: 2rem; font-size: 1.2rem; z-index: 800; }}
  .nav-links.active {{ display: flex; }}
  .hamburger {{ display: block; z-index: 1000; position: relative; }}
}}
"""


# ─────────────────────────────────────────────
#  JavaScript
# ─────────────────────────────────────────────

def generate_js_code(submit_message: str) -> str:
    """Build the JavaScript code block."""
    return f"""/* SiteGen AI — Fallback Template Scripts */

document.addEventListener('DOMContentLoaded', () => {{
    // ── Mobile Nav ──────────────────────────────────────────
    const hamburger = document.getElementById('menu-hamburger');
    const navMenu   = document.getElementById('nav-menu');
    if (hamburger && navMenu) {{
        hamburger.addEventListener('click', (e) => {{
            e.stopPropagation();
            navMenu.classList.toggle('active');
            const icon = hamburger.querySelector('i');
            if (icon) icon.className = navMenu.classList.contains('active') ? 'fas fa-times' : 'fas fa-bars';
        }});
        navMenu.querySelectorAll('a').forEach(link => {{
            link.addEventListener('click', () => {{
                navMenu.classList.remove('active');
                const icon = hamburger.querySelector('i');
                if (icon) icon.className = 'fas fa-bars';
            }});
        }});
        document.addEventListener('click', (e) => {{
            if (!navMenu.contains(e.target) && !hamburger.contains(e.target)) {{
                navMenu.classList.remove('active');
                const icon = hamburger.querySelector('i');
                if (icon) icon.className = 'fas fa-bars';
            }}
        }});
    }}

    // ── Navbar scroll style ──────────────────────────────────
    const navbar = document.getElementById('navbar');
    if (navbar) {{
        window.addEventListener('scroll', () => {{
            navbar.style.boxShadow = window.scrollY > 10 ? '0 4px 24px rgba(0,0,0,0.2)' : '';
        }});
    }}

    // ── Scroll fade-in animations ────────────────────────────
    const observer = new IntersectionObserver((entries) => {{
        entries.forEach(entry => {{
            if (entry.isIntersecting) {{
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }}
        }});
    }}, {{ threshold: 0.1 }});
    document.querySelectorAll('.service-card, .skills-card').forEach(el => {{
        el.style.opacity = '0';
        el.style.transform = 'translateY(24px)';
        el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        observer.observe(el);
    }});

    // ── Contact form ─────────────────────────────────────────
    const form = document.getElementById('simulated-contact-form');
    if (form) {{
        form.addEventListener('submit', (e) => {{
            e.preventDefault();
            showNotification("{submit_message}");
            form.reset();
        }});
    }}
}});

function showNotification(message) {{
    const old = document.getElementById('sitegen-notify');
    if (old) old.remove();
    const div = document.createElement('div');
    div.id = 'sitegen-notify';
    Object.assign(div.style, {{
        position: 'fixed', bottom: '2rem', right: '2rem',
        background: 'var(--accent)', color: '#fff',
        padding: '1rem 1.5rem', borderRadius: '10px',
        boxShadow: '0 10px 30px rgba(0,0,0,0.3)',
        fontFamily: "'Inter', sans-serif", fontSize: '0.9rem',
        fontWeight: '500', display: 'flex', alignItems: 'center',
        gap: '0.75rem', zIndex: '99999',
        opacity: '0', transform: 'translateY(20px)',
        transition: 'all 0.3s ease',
    }});
    div.innerHTML = '<i class="fas fa-check-circle" style="font-size:1.1rem"></i><span>' + message + '</span>';
    document.body.appendChild(div);
    setTimeout(() => {{ div.style.opacity = '1'; div.style.transform = 'translateY(0)'; }}, 50);
    setTimeout(() => {{
        div.style.opacity = '0'; div.style.transform = 'translateY(20px)';
        setTimeout(() => div.remove(), 300);
    }}, 5000);
}}
"""
