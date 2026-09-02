from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os

app = Flask(__name__)
CORS(app)

# ============================================================
# CONFIGURATION
# ============================================================

# IMPORTANT:
# Replace this with your AUTHORIZED college/training website.
BASE_URL = "https://moviesdatamil.me"

START_URL = (
    "https://moviesdatamil.me/tamil-2026-movies/"
)


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

TIMEOUT = 20


# ============================================================
# HTTP / SOUP
# ============================================================

def get_soup(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=TIMEOUT
    )

    response.raise_for_status()

    return BeautifulSoup(
        response.text,
        "html.parser"
    )


# ============================================================
# MOVIE / CLASS LIST
# ============================================================

def scrape_movies():

    movies = []

    try:
        soup = get_soup(START_URL)

        # ----------------------------------------------------
        # CHANGE THIS SELECTOR according to your college site.
        #
        # Example:
        # div.f a
        # ----------------------------------------------------

        for item in soup.select("div.f"):

            anchor = item.select_one("a")

            if not anchor:
                continue

            name = anchor.get_text(
                " ",
                strip=True
            )

            href = anchor.get("href")

            if not href:
                continue

            link = urljoin(
                BASE_URL,
                href
            )

            if not name:
                continue

            movies.append({
                "name": name,
                "link": link
            })

    except Exception as e:

        print("Error scraping movies:", e)

        raise

    return movies


# ============================================================
# FILE / VIDEO LINKS
# ============================================================

def get_files(url):

    soup = get_soup(url)

    files = []

    for folder in soup.select("div.folder"):

        anchor = folder.select_one(
            "div.left a"
        )

        if not anchor:
            continue

        file_name = anchor.get_text(
            " ",
            strip=True
        )

        href = anchor.get("href")

        if not href:
            continue

        file_link = urljoin(
            BASE_URL,
            href
        )

        size_element = folder.select_one(
            "li:nth-of-type(2)"
        )

        format_element = folder.select_one(
            "li:nth-of-type(3)"
        )

        file_size = (
            size_element.get_text(
                " ",
                strip=True
            )
            if size_element
            else ""
        )

        file_format = (
            format_element.get_text(
                " ",
                strip=True
            )
            if format_element
            else ""
        )

        files.append({
            "name": file_name,
            "link": file_link,
            "size": file_size,
            "format": file_format
        })

    return files


# ============================================================
# QUALITY
# ============================================================

def get_quality(text):

    text = text.lower()

    if "1080" in text:
        return "1080"

    if "720" in text:
        return "720"

    if "360" in text:
        return "360"

    return None


# ============================================================
# ADD UNIQUE
# ============================================================

def add_unique(array, value):

    if not value:
        return

    if value not in array:
        array.append(value)


# ============================================================
# SCRAPE SELECTED CLASS / VIDEO
# ============================================================

def scrape_movie(movie_name, movie_link):

    result = {
        "name": movie_name,
        "link": movie_link,
        "season": [],
        "360": [],
        "720": [],
        "1080": []
    }

    soup = get_soup(movie_link)

    # --------------------------------------------------------
    # Find sub sections / videos
    # --------------------------------------------------------

    for item in soup.select("div.f"):

        anchor = item.select_one("a")

        if not anchor:
            continue

        sub_name = anchor.get_text(
            " ",
            strip=True
        )

        href = anchor.get("href")

        if not href:
            continue

        sub_link = urljoin(
            BASE_URL,
            href
        )

        if not sub_name:
            continue

        # ----------------------------------------------------
        # SEASON
        # ----------------------------------------------------

        if "season" in sub_name.lower():

            result["season"].append({
                "name": sub_name,
                "link": sub_link
            })

            continue

        # ----------------------------------------------------
        # QUALITY
        # ----------------------------------------------------

        quality = get_quality(sub_name)

        # ----------------------------------------------------
        # If this is a sub-page, inspect it
        # ----------------------------------------------------

        try:

            sub_soup = get_soup(sub_link)

        except Exception as e:

            print(
                "Error opening:",
                sub_link,
                e
            )

            continue

        found_files = False

        # ----------------------------------------------------
        # Files / videos
        # ----------------------------------------------------

        for final_item in sub_soup.select("div.f"):

            final_anchor = final_item.select_one("a")

            if not final_anchor:
                continue

            final_name = final_anchor.get_text(
                " ",
                strip=True
            )

            final_href = final_anchor.get("href")

            if not final_href:
                continue

            final_link = urljoin(
                BASE_URL,
                final_href
            )

            final_quality = get_quality(
                final_name
            )

            current_quality = (
                final_quality
                or quality
            )

            if not current_quality:
                continue

            found_files = True

            video_data = {
                "name": final_name,
                "link": final_link,
                "size": "",
                "format": "",
                "text": final_name
            }

            add_unique(
                result[current_quality],
                video_data
            )

        # ----------------------------------------------------
        # Direct page itself as fallback
        # ----------------------------------------------------

        if not found_files and quality:

            video_data = {
                "name": sub_name,
                "link": sub_link,
                "size": "",
                "format": "",
                "text": sub_name
            }

            add_unique(
                result[quality],
                video_data
            )

    return result


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# MOVIES API
# ============================================================

@app.route("/movies")
def movies():

    try:

        data = scrape_movies()

        return jsonify({
            "success": True,
            "movies": data,
            "count": len(data)
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e),
            "movies": []
        }), 500


# ============================================================
# SELECTED MOVIE / CLASS API
# ============================================================

@app.route(
    "/movie",
    methods=["POST"]
)
def movie():

    try:

        data = request.get_json(
            silent=True
        )

        if not data:

            return jsonify({
                "success": False,
                "error": "Request body is empty"
            }), 400

        movie_name = data.get(
            "name"
        )

        movie_link = data.get(
            "link"
        )

        if not movie_name:

            return jsonify({
                "success": False,
                "error": "Movie/class name is required"
            }), 400

        if not movie_link:

            return jsonify({
                "success": False,
                "error": "Movie/class link is required"
            }), 400

        result = scrape_movie(
            movie_name,
            movie_link
        )

        return jsonify({
            "success": True,
            "data": result
        })

    except requests.RequestException as e:

        return jsonify({
            "success": False,
            "error": f"Website request failed: {str(e)}"
        }), 502

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "ok"
    })


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
