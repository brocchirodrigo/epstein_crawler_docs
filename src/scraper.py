"""
Web scraping module for the Epstein Files Scraper.
Handles browser automation, gate passing, and PDF link collection.
"""

import time
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.sync_api import Page

from .config import settings, HTML_PARSER, NO_RESULTS_TEXT
from .logging_config import logger


def create_browser_context(playwright) -> tuple:
    """
    Creates a Playwright browser and context with anti-detection settings.
    Returns (browser, context, page) tuple.
    """
    browser = playwright.chromium.launch(
        headless=settings.headless,
        args=settings.browser_args,
    )

    context = browser.new_context(
        viewport=settings.viewport,
        user_agent=settings.user_agent,
        accept_downloads=True,
        locale="en-US",
        timezone_id="America/New_York",
        permissions=["geolocation"],
        color_scheme="light",
    )

    page = context.new_page()

    # Comprehensive stealth patches
    page.add_init_script("""
        // Hide webdriver
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        delete navigator.__proto__.webdriver;

        // Fake plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = [
                    {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                    {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                    {name: 'Native Client', filename: 'internal-nacl-plugin'}
                ];
                plugins.item = (i) => plugins[i];
                plugins.namedItem = (name) => plugins.find(p => p.name === name);
                plugins.refresh = () => {};
                return plugins;
            }
        });

        // Fake languages
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});

        // Fake Chrome runtime
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };

        // Fake permissions query
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({state: Notification.permission}) :
                originalQuery(parameters)
        );

        // Fake WebGL vendor/renderer
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel Iris OpenGL Engine';
            return getParameter.apply(this, arguments);
        };

        // Fake connection rtt
        if (navigator.connection) {
            Object.defineProperty(navigator.connection, 'rtt', {get: () => 50});
        }
    """)

    return browser, context, page


def pass_gates(page: Page) -> None:
    """
    Passes through robot check and age verification gates using JavaScript clicks.
    Checks page content before attempting clicks to handle cached sessions.
    """
    time.sleep(2)
    content = page.content()

    if "I am not a robot" in content:
        logger.info("🤖 Clicking 'I am not a robot'...")
        try:
            page.evaluate("""() => {
                const btn = document.querySelector('input.usa-button[value="I am not a robot"]');
                if (btn) btn.click();
            }""")
            time.sleep(3)
        except Exception as e:
            logger.error(f"Failed to click robot button: {e}")

    content = page.content()
    if "Are you 18 years of age" in content:
        logger.info("🔞 Clicking 'Yes' (18+)...")
        try:
            page.evaluate("""() => {
                const btn = document.getElementById('age-button-yes');
                if (btn) btn.click();
            }""")
            time.sleep(3)
            page.wait_for_load_state("networkidle")
        except Exception as e:
            logger.error(f"Failed to click age verification: {e}")
    else:
        logger.info("✅ Already verified (cookies)")


def _check_results_loaded(content: str) -> bool:
    """Check if results are present in the page content."""
    soup = BeautifulSoup(content, HTML_PARSER)
    results_div = soup.find("div", id="results")
    if results_div and results_div.find_all("a", href=lambda x: x and ".pdf" in str(x).lower()):
        return True
    return False


def _wait_for_results(page: Page, max_wait: int = 60) -> bool:
    """
    Wait for search results to load.
    Returns True if results loaded, False if timeout.
    """
    waited = 0

    while waited < max_wait:
        time.sleep(5)
        waited += 5
        content = page.content()

        # Check for loading indicator - must be display:block not display:none
        loading_visible = 'id="loadingMessage" style="display: block' in content

        if loading_visible:
            logger.info(f"  Still loading... ({waited}s)")
            continue

        # Check for results
        if "Showing" in content and "Results" in content:
            logger.info(f"✅ Results loaded after {waited}s")
            return True

        # Check if actual PDF links exist
        if _check_results_loaded(content):
            logger.info(f"✅ Results loaded after {waited}s (found PDFs)")
            return True

        # "No results" after waiting enough
        if waited >= 15 and "different search" in content.lower():
            logger.warning("No results found for this search")
            return True

    logger.warning(f"Timeout after {waited}s waiting for results")
    return False


def search_letter(page: Page, letter: str) -> bool:
    """
    Performs a search for the given letter in the search input.
    Returns True if search was successful.
    """
    logger.info(f"📝 Searching for '{letter}'...")

    try:
        page.evaluate("window.scrollTo(0, 500)")
        time.sleep(2)

        # Use native Playwright methods for better headless compatibility
        search_input = page.locator("#searchInput")
        search_button = page.locator("#searchButton")

        if not search_input.count():
            logger.error("Search input not found on page")
            return False

        # Clear and type using native methods
        search_input.fill("")
        search_input.fill(letter)
        time.sleep(0.5)

        # Click search button
        search_button.click()

        logger.info("⏳ Waiting for results to load (this may take 20-30 seconds)...")
        return _wait_for_results(page, max_wait=60)

    except Exception as e:
        logger.error(f"Search failed for letter '{letter}': {e}")
        return False


def get_total_pages(page: Page, max_pages: int = None) -> int:
    """
    Extracts total number of result pages from pagination label.
    Returns min(total_pages, max_pages) if max_pages is specified.
    """
    content = page.content()
    
    match = re.search(r"Showing \d+ to \d+ of ([\d,]+) Results", content)

    if not match:
        soup = BeautifulSoup(content, HTML_PARSER)
        results_div = soup.find("div", id="results")
        if results_div:
            links = results_div.find_all("a", href=lambda x: x and ".pdf" in str(x).lower())
            if links:
                logger.info(f"📊 Found {len(links)} PDFs on page (no pagination label)")
                return max_pages if max_pages else 1
        
        if NO_RESULTS_TEXT in content:
            logger.warning("No results found for this search")
            return 0
            
        logger.warning("Could not find pagination label, assuming 1 page")
        return 1

    total_results = int(match.group(1).replace(",", ""))
    total_pages = (total_results + 9) // 10

    logger.info(f"📊 {total_results:,} results across {total_pages} pages")

    if max_pages:
        pages_to_process = min(total_pages, max_pages)
        logger.info(f"📖 Will process {pages_to_process} pages (limit: {max_pages})")
        return pages_to_process
    return total_pages


def extract_pdfs_from_page(page: Page) -> list:
    """
    Extracts PDF links from the current results page.
    Returns list of dicts with url, filename, and dataset.
    """
    pdfs = []

    try:
        content = page.content()
        soup = BeautifulSoup(content, HTML_PARSER)
        results_div = soup.find("div", id="results")

        if not results_div:
            logger.warning("Results container #results not found")
            return pdfs

        links = results_div.find_all("a", href=lambda x: x and ".pdf" in str(x).lower())

        for link in links:
            href = link.get("href", "")
            filename = link.get_text(strip=True)
            full_url = urljoin(settings.base_url, href)

            dataset = ""
            h3 = link.find_parent("h3")
            if h3:
                text = h3.get_text()
                if " - " in text:
                    dataset = text.split(" - ")[-1].strip()

            pdfs.append({"url": full_url, "filename": filename, "dataset": dataset})

    except Exception as e:
        logger.error(f"Failed to extract PDFs: {e}")

    return pdfs


def navigate_to_page(page: Page, target_page: int) -> bool:
    """
    Navigates to a specific page number by clicking pagination buttons.
    Returns True if navigation was successful and page has content.
    """
    try:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

        clicked = page.evaluate(f"""() => {{
            const buttons = document.querySelectorAll('.usa-pagination__button, .usa-pagination a');
            for (const btn of buttons) {{
                if (btn.textContent.trim() === '{target_page}') {{
                    btn.click();
                    return true;
                }}
            }}
            return false;
        }}""")

        if not clicked:
            logger.warning(f"  Page {target_page} button not found")
            return False

        logger.info(f"  ⏳ Loading page {target_page}...")
        time.sleep(5)
        page.wait_for_load_state("networkidle")
        page.evaluate("window.scrollTo(0, 500)")
        time.sleep(2)

        content = page.content()
        if NO_RESULTS_TEXT in content:
            logger.warning(f"  Page {target_page} is empty")
            return False

        soup = BeautifulSoup(content, HTML_PARSER)
        results_div = soup.find("div", id="results")
        if not results_div or not results_div.find_all("a", href=lambda x: x and ".pdf" in str(x).lower()):
            logger.warning(f"  Page {target_page} has no PDFs")
            return False

        return True

    except Exception as e:
        logger.error(f"Navigation to page {target_page} failed: {e}")
        return False


def collect_pdfs_for_letter(page: Page, letter: str, max_pages: int = None) -> list:
    """
    Collects all PDF links for a given letter by iterating through result pages.
    Returns list of PDF info dicts.
    """
    all_pdfs = []

    if not search_letter(page, letter):
        return all_pdfs

    total_pages = get_total_pages(page, max_pages)
    if total_pages == 0:
        return all_pdfs

    logger.info(f"  📄 Page 1/{total_pages} - Extracting links...")
    pdfs = extract_pdfs_from_page(page)
    all_pdfs.extend(pdfs)
    logger.info(f"  ✅ Page 1/{total_pages} - Found {len(pdfs)} PDFs (total: {len(all_pdfs)})")

    for page_num in range(2, total_pages + 1):
        logger.info(f"  ➡️ Navigating to page {page_num}...")

        if not navigate_to_page(page, page_num):
            logger.warning(f"  ⚠️ Stopping at page {page_num - 1}")
            break

        logger.info(f"  📄 Page {page_num}/{total_pages} - Extracting links...")
        pdfs = extract_pdfs_from_page(page)

        if not pdfs:
            logger.warning(f"  ⚠️ No PDFs found on page {page_num}, stopping")
            break

        all_pdfs.extend(pdfs)
        logger.info(f"  ✅ Page {page_num}/{total_pages} - Found {len(pdfs)} PDFs (total: {len(all_pdfs)})")

    return all_pdfs
