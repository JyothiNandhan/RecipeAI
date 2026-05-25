from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Listen to console and network errors
        page.on("console", lambda msg: print(f"CONSOLE: {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"PAGE_ERROR: {err}"))
        page.on("requestfailed", lambda req: print(f"NETWORK_FAIL: {req.url} - {req.failure}"))
        page.on("response", lambda resp: print(f"RESPONSE: {resp.status} {resp.url}") if resp.status >= 400 else None)

        print("Navigating to register page...")
        page.goto("http://localhost:4200/register")

        print("Filling form...")
        page.fill("input[name='email']", "playwright_user@example.com")
        page.fill("input[name='password']", "short")
        page.fill("input[name='confirmPassword']", "short")
        
        print("Clicking submit...")
        page.click("button[type='submit']")
        
        # Wait a bit for the network request
        page.wait_for_timeout(3000)
        
        print("Checking for error message on screen...")
        try:
            error_el = page.wait_for_selector(".error-msg", timeout=2000)
            if error_el:
                print(f"UI ERROR SHOWN: {error_el.inner_text()}")
        except Exception:
            print("No UI error message shown.")

        print("Testing login now...")
        page.goto("http://localhost:4200/login")
        page.fill("input[name='email']", "playwright_user@example.com")
        page.fill("input[name='password']", "short")
        page.click("button[type='submit']")
        
        page.wait_for_timeout(3000)
        
        try:
            error_el = page.wait_for_selector(".error-msg", timeout=2000)
            if error_el:
                print(f"UI ERROR SHOWN: {error_el.inner_text()}")
        except Exception:
            print("No UI error message shown.")
            
        print("Current URL:", page.url)

        browser.close()

if __name__ == "__main__":
    run()
