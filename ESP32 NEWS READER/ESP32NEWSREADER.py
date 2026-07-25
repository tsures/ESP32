from machine import Pin, I2C
import network
import urequests
import time
import ssd1306

# -----------------------------
# Configuration
# -----------------------------
WIFI_SSID = "Wokwi-GUEST"
WIFI_PASSWORD = ""

RSS_URL = "https://www.ynet.co.il/Integration/StoryRss2.xml"

ARTICLE_DISPLAY_SECONDS = 4
RSS_REFRESH_SECONDS = 10 * 60

HEBREW_FONT = {
    'א': (0, 0, 68, 36, 52, 72, 72, 68, 0, 0),
    'ב': (0, 0, 120, 4, 4, 4, 4, 126, 0, 0),
    'ג': (0, 0, 96, 16, 16, 16, 16, 104, 0, 0),
    'ד': (0, 0, 124, 8, 8, 8, 8, 8, 0, 0),
    'ה': (0, 0, 120, 4, 4, 68, 68, 68, 0, 0),
    'ו': (0, 0, 64, 64, 64, 64, 64, 64, 0, 0),
    'ז': (0, 0, 112, 32, 32, 32, 32, 32, 0, 0),
    'ח': (0, 0, 120, 68, 68, 68, 68, 68, 0, 0),
    'ט': (0, 0, 92, 66, 66, 66, 66, 60, 0, 0),
    'י': (0, 0, 64, 64, 64, 64, 0, 0, 0, 0),
    'ך': (0, 0, 112, 8, 8, 8, 8, 8, 8, 8),
    'כ': (0, 0, 120, 4, 4, 4, 4, 120, 0, 0),
    'ל': (64, 64, 124, 4, 8, 8, 8, 16, 0, 0),
    'ם': (0, 0, 120, 68, 68, 68, 68, 124, 0, 0),
    'מ': (0, 0, 92, 34, 34, 34, 66, 78, 0, 0),
    'ן': (0, 0, 64, 64, 64, 64, 64, 64, 64, 64),
    'נ': (0, 0, 96, 16, 16, 16, 16, 112, 0, 0),
    'ס': (0, 0, 124, 66, 66, 66, 66, 60, 0, 0),
    'ע': (0, 0, 68, 68, 36, 36, 40, 48, 64, 0),
    'ף': (0, 0, 120, 68, 100, 4, 4, 4, 4, 4),
    'פ': (0, 0, 120, 68, 100, 4, 4, 120, 0, 0),
    'ץ': (0, 0, 68, 36, 24, 16, 16, 16, 16, 16),
    'צ': (0, 0, 68, 36, 20, 8, 8, 124, 0, 0),
    'ק': (0, 0, 126, 2, 4, 68, 68, 72, 64, 64),
    'ר': (0, 0, 120, 4, 4, 4, 4, 4, 0, 0),
    'ש': (0, 0, 73, 73, 114, 34, 36, 56, 0, 0),
    'ת': (0, 0, 124, 34, 34, 34, 34, 98, 0, 0)
}

# -----------------------------
# OLED
# -----------------------------
i2c = I2C(0, scl=Pin(22), sda=Pin(21))

oled_width = 128
oled_height = 64

oled = ssd1306.SSD1306_I2C(
    oled_width,
    oled_height,
    i2c
)

def is_hebrew(character):
    character_code = ord(character)
    return 0x0590 <= character_code <= 0x05FF


def draw_hebrew_character(character, x, y):
    bitmap = HEBREW_FONT.get(character)

    if bitmap is None:
        return

    for row in range(10):
        row_data = bitmap[row]

        for column in range(8):
            mask = 1 << (7 - column)

            if row_data & mask:
                oled.pixel(x + column, y + row, 1)


def draw_display_character(character, x, y):
    if is_hebrew(character):
        draw_hebrew_character(character, x, y)

    elif character != " " and 32 <= ord(character) <= 126:
        oled.text(character, x, y)


def draw_rtl_line(text, y):
    x = 120
    index = 0

    while index < len(text) and x >= 0:
        character = text[index]

        if character == " ":
            x -= 8
            index += 1
            continue

        if is_hebrew(character):
            draw_display_character(character, x, y)
            x -= 8
            index += 1
            continue

        # Keep numbers and English text in left-to-right order
        run_end = index

        while run_end < len(text):
            run_character = text[run_end]

            if run_character == " " or is_hebrew(run_character):
                break

            run_end += 1

        ascii_run = text[index:run_end]

        for run_character in reversed(ascii_run):
            if x < 0:
                break

            draw_display_character(run_character, x, y)
            x -= 8

        index = run_end

def show_message(line1, line2=""):
    oled.fill(0)
    oled.text(line1[:16], 0, 16)
    oled.text(line2[:16], 0, 32)
    oled.show()


# -----------------------------
# Wi-Fi
# -----------------------------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        show_message("Connecting WiFi")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        timeout = 20

        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1

    if wlan.isconnected():
        ip_address = wlan.ifconfig()[0]
        print("Wi-Fi connected:", ip_address)
        show_message("WiFi connected", ip_address)
        time.sleep(2)
        return True

    show_message("WiFi failed")
    return False


# -----------------------------
# Text processing
# -----------------------------
def remove_html_tags(text):
    result = ""
    inside_tag = False

    for character in text:
        if character == "<":
            inside_tag = True
        elif character == ">":
            inside_tag = False
        elif not inside_tag:
            result += character

    return result


def clean_text(text):
    text = text.replace("<![CDATA[", "")
    text = text.replace("]]>", "")
    text = remove_html_tags(text)

    replacements = {
        "&amp;": "&",
        "&quot;": '"',
        "&#39;": "'",
        "&apos;": "'",
        "&lt;": "<",
        "&gt;": ">",
        "&nbsp;": " "
    }

    for old_value, new_value in replacements.items():
        text = text.replace(old_value, new_value)

    # Remove new lines and repeated spaces
    text = text.replace("\r", " ")
    text = text.replace("\n", " ")

    while "  " in text:
        text = text.replace("  ", " ")

    return text.strip()


def extract_titles(xml):
    titles = []
    current_position = 0

    while True:
        item_start = xml.find("<item>", current_position)

        if item_start == -1:
            break

        item_end = xml.find("</item>", item_start)

        if item_end == -1:
            break

        item_content = xml[item_start:item_end]

        title_start = item_content.find("<title>")
        title_end = item_content.find("</title>")

        if title_start != -1 and title_end != -1:
            title_start += len("<title>")

            title = item_content[title_start:title_end]
            title = clean_text(title)

            if title:
                titles.append(title)

        current_position = item_end + len("</item>")

    return titles

def download_news():
    response = None

    try:
        show_message("Downloading", "news...")
        print("Downloading:", RSS_URL)

        response = urequests.get(RSS_URL)
        xml = response.text

        titles = extract_titles(xml)

        print("Articles found:", len(titles))
        return titles

    except Exception as error:
        print("RSS error:", error)
        show_message("RSS error", str(error))
        time.sleep(3)
        return []

    finally:
        if response is not None:
            response.close()


# -----------------------------
# OLED display
# -----------------------------
def wrap_text(text, characters_per_line=16):
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        if not current_line:
            test_line = word
        else:
            test_line = current_line + " " + word

        if len(test_line) <= characters_per_line:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)

            while len(word) > characters_per_line:
                lines.append(word[:characters_per_line])
                word = word[characters_per_line:]

            current_line = word

    if current_line:
        lines.append(current_line)

    return lines

def display_article(title, article_number, total_articles):
    lines = wrap_text(title, 16)
    lines = lines[:5]

    oled.fill(0)

    counter = "{}/{}".format(article_number, total_articles)
    oled.text(counter, 0, 0)

    for x in range(128):
        oled.pixel(x, 9, 1)

    y = 12

    for line in lines:
        draw_rtl_line(line, y)
        y += 10

    oled.show()

# -----------------------------
# Main program
# -----------------------------
if not connect_wifi():
    while True:
        time.sleep(1)

while True:
    news_titles = download_news()

    if not news_titles:
        show_message("No news found", "Retrying...")
        time.sleep(30)
        continue

    refresh_started = time.time()

    while time.time() - refresh_started < RSS_REFRESH_SECONDS:
        for index, title in enumerate(news_titles):
            print(index + 1, title)

            display_article(
                title,
                index + 1,
                len(news_titles)
            )

            time.sleep(ARTICLE_DISPLAY_SECONDS)

            if time.time() - refresh_started >= RSS_REFRESH_SECONDS:
                break
