# Kjell.com Product Description Generator

A tool that takes a product URL from kjell.com, scrapes the product data, and uses an AI model to write a short Swedish marketing description for it.

---

## What it does

1. You give it a kjell.com product URL
2. It extracts the product data embedded in the page (name, price, features, rating, etc.)
3. It sends that data to an AI language model (via Groq)
4. The model writes a concise Swedish product description following copywriting rules
5. You get the result printed to the terminal, or saved to a JSON file if running in batch mode

---

## Project structure

```
website.py               — Scrapes a kjell.com page and returns structured product data
description_generator.py — Takes that data and calls the Groq API to generate a description
main_pipeline.py         — Ties the two together; this is what you run
requirements.txt         — Python dependencies
.env                     — Your API key goes here (not committed to git)
```

---

## How the scraper works

Kjell.com embeds all product information as a JSON object directly in the page source, assigned to a JavaScript variable called `window.CURRENT_PAGE`. Instead of parsing HTML elements, `website.py` extracts that JSON with a regex, then pulls out the fields that are useful for copywriting: product name, brand, price, discount, USPs, description text, customer rating, and so on.

This is more reliable than HTML scraping because it does not depend on CSS class names or page layout, which tend to change.

---

## How the description generator works

`description_generator.py` takes the scraped data, formats it into a prompt, and sends it to `llama-3.3-70b-versatile` running on Groq. The prompt instructs the model to write 3–5 sentences in Swedish, lead with the strongest benefit, mention key features, note any discount or rating, and end with a soft call to action. It is told not to copy the existing description verbatim and not to use bullet points or emojis.

---

## Setup

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

**2. Create a `.env` file in the project root**

```
Groq_API_Key=your_key_here
```

Get a free API key at [console.groq.com](https://console.groq.com).

---

## Usage

**Single product**

```bash
python main_pipeline.py https://www.kjell.com/se/produkter/...
```

**Multiple products from a file** (one URL per line)

```bash
python main_pipeline.py --batch urls.txt
```

Results are saved to `batch_descriptions.json` in the same directory.

**No arguments** — runs the two demo URLs hardcoded in `DEMO_URLS` at the bottom of `main_pipeline.py`

```bash
python main_pipeline.py
```

---

## Requirements

- Python 3.10+
- A Groq API key (free tier is sufficient)
- Internet access to reach kjell.com and the Groq API
