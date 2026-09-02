from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


app = Flask(__name__)

CORS(app)


# ==========================================================
# CONFIGURATION
# ==========================================================

BASE_URL = "https://moviesdatamil.me"

START_URL = (
    "https://moviesdatamil.me/tamil-2026-movies/"
)


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


# ==========================================================
# GET SOUP
# ==========================================================

def get_soup(url):

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=15
    )

    response.raise_for_status()

    return BeautifulSoup(
        response.text,
        "html.parser"
    )


# ==========================================================
# HOME
# ==========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ==========================================================
# GET ALL MAIN ITEMS
#
# This endpoint ONLY gets the main names + links.
# ==========================================================

@app.route("/movies")
def get_movies():

    movies = []

    try:

        soup = get_soup(
            START_URL
        )


        # --------------------------------------------------
        # Find total pages
        # --------------------------------------------------

        total_element = soup.find(
            "span",
            id="totalPages"
        )


        if total_element:

            total_pages = int(
                total_element.get_text(
                    strip=True
                )
            )

        else:

            total_pages = 1


        # --------------------------------------------------
        # ALL PAGES EXCEPT LAST
        # --------------------------------------------------

        for page in range(
            1,
            total_pages
        ):


            if page == 1:

                page_url = START_URL

            else:

                page_url = (
                    f"{START_URL}?page={page}"
                )


            # First page already loaded

            if page == 1:

                page_soup = soup

            else:

                page_soup = get_soup(
                    page_url
                )


            # ------------------------------------------------
            # Main items
            # ------------------------------------------------

            for item in page_soup.select(
                "div.f"
            ):

                anchor = item.find(
                    "a"
                )


                if not anchor:

                    continue


                name = anchor.get_text(
                    strip=True
                )


                href = anchor.get(
                    "href"
                )


                if not href:

                    continue


                link = urljoin(
                    BASE_URL,
                    href
                )


                movies.append({

                    "name": name,

                    "link": link

                })


        return jsonify({

            "success": True,

            "total": len(movies),

            "movies": movies

        })


    except Exception as e:

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# ==========================================================
# GET FIRST SERVER LINK
# ==========================================================

def get_first_server(url):

    soup = get_soup(
        url
    )


    link = soup.select_one(
        "div.dlink a"
    )


    if not link:

        return None


    return {

        "text": link.get_text(
            " ",
            strip=True
        ),

        "link": urljoin(
            BASE_URL,
            link.get("href")
        )

    }


# ==========================================================
# FOLLOW SERVER LEVELS
# ==========================================================

def get_level_3_link(
    url,
    max_depth=3
):

    current_url = url

    visited = set()

    result = None


    for level in range(
        1,
        max_depth + 1
    ):


        if current_url in visited:

            break


        visited.add(
            current_url
        )


        try:

            download = get_first_server(
                current_url
            )

        except Exception:

            break


        if not download:

            break


        result = {

            "level": level,

            "text": download["text"],

            "link": download["link"]

        }


        current_url = download[
            "link"
        ]


    return result


# ==========================================================
# GET FILES
# ==========================================================

def get_files(url):

    soup = get_soup(
        url
    )

    files = []


    for folder in soup.select(
        "div.folder"
    ):


        anchor = folder.select_one(
            "div.left a"
        )


        if not anchor:

            continue


        file_name = anchor.get_text(
            strip=True
        )


        file_link = urljoin(
            BASE_URL,
            anchor.get("href")
        )


        size_element = folder.select_one(
            "li:nth-of-type(2)"
        )


        format_element = folder.select_one(
            "li:nth-of-type(3)"
        )


        file_size = (

            size_element.get_text(
                strip=True
            )

            if size_element

            else ""

        )


        file_format = (

            format_element.get_text(
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


# ==========================================================
# GET QUALITY
# ==========================================================

def get_quality(text):

    text = text.lower()


    if "1080" in text:

        return "1080"


    if "720" in text:

        return "720"


    if "360" in text:

        return "360"


    return None


# ==========================================================
# ADD UNIQUE LINK
# ==========================================================

def add_unique(
    array,
    value
):

    if not value:

        return


    if value not in array:

        array.append(
            value
        )


# ==========================================================
# SCRAPE SELECTED MOVIE / CLASS
# ==========================================================

@app.route(
    "/movie",
    methods=["POST"]
)
def scrape_movie():

    data = request.get_json()


    if not data:

        return jsonify({

            "success": False,

            "error": "No JSON data"

        }), 400


    movie_name = data.get(
        "name"
    )


    movie_link = data.get(
        "link"
    )


    if not movie_name or not movie_link:

        return jsonify({

            "success": False,

            "error": "Name and link are required"

        }), 400


    result = {

        "name": movie_name,

        "link": movie_link,

        "season": [],

        "360": [],

        "720": [],

        "1080": []

    }


    try:

        # ==================================================
        # OPEN MAIN PAGE
        # ==================================================

        movie_soup = get_soup(
            movie_link
        )


        # ==================================================
        # SUB ITEMS
        # ==================================================

        for sub_item in movie_soup.select(
            "div.f"
        ):


            sub_anchor = sub_item.find(
                "a"
            )


            if not sub_anchor:

                continue


            sub_name = sub_anchor.get_text(
                strip=True
            )


            sub_link = urljoin(
                BASE_URL,
                sub_anchor.get("href")
            )


            # ==================================================
            # SEASON
            # ==================================================

            if "season" in sub_name.lower():

                result["season"].append({

                    "name": sub_name,

                    "link": sub_link

                })

                continue


            # ==================================================
            # DETECT QUALITY FROM SUB NAME
            # ==================================================

            quality = get_quality(
                sub_name
            )


            # ==================================================
            # OPEN SUB PAGE
            # ==================================================

            try:

                sub_soup = get_soup(
                    sub_link
                )


            except Exception:

                continue


            # ==================================================
            # FINAL LINKS
            # ==================================================

            final_items = sub_soup.select(
                "div.f"
            )


            # If the sub page itself is
            # already a final page

            if not final_items:

                final_items = []


            for final_item in final_items:


                final_anchor = final_item.find(
                    "a"
                )


                if not final_anchor:

                    continue


                final_name = final_anchor.get_text(
                    strip=True
                )


                final_link = urljoin(
                    BASE_URL,
                    final_anchor.get("href")
                )


                # ------------------------------------------
                # Detect quality
                # ------------------------------------------

                final_quality = get_quality(
                    final_name
                )


                if final_quality:

                    quality = final_quality


                if not quality:

                    continue


                # ==================================================
                # OPEN FINAL PAGE
                # ==================================================

                try:

                    files = get_files(
                        final_link
                    )

                except Exception:

                    continue


                # ==================================================
                # EVERY FILE
                # ==================================================

                for file in files:


                    try:

                        level_3 = get_level_3_link(
                            file["link"],
                            max_depth=3
                        )

                    except Exception:

                        continue


                    if not level_3:

                        continue


                    # ==================================================
                    # SAVE FINAL LINK
                    # ==================================================

                    add_unique(

                        result[quality],

                        {

                            "name":
                                file["name"],

                            "size":
                                file["size"],

                            "format":
                                file["format"],

                            "text":
                                level_3["text"],

                            "link":
                                level_3["link"]

                        }

                    )


        # ==================================================
        # RETURN RESULT
        # ==================================================

        return jsonify({

            "success": True,

            "data": result

        })


    except Exception as e:

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
