import hashlib, secrets, base64, webbrowser, requests

def main():
    code_verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    login_url = (
        "https://app-api.pixiv.net/web/v1/login"
        f"?code_challenge={code_challenge}"
        "&code_challenge_method=S256"
        "&client=pixiv-android"
    )

    print("\nOpening browser, please log in to Pixiv...")
    print(f"(or manually copy this link into your browser):\n{login_url}\n")
    webbrowser.open(login_url)

    print("After logging in, the address bar URL will look like:")
    print("  ...callback?state=xxx&code=XXXXXXXXXX\n")
    print("Copy only the part after code= (not including code= itself):")

    code = input(">>> ").strip()

    if "code=" in code:
        code = code.split("code=")[-1].split("&")[0].strip()

    print(f"\nUsing code: {code[:12]}... to exchange for token...")

    res = requests.post(
        "https://oauth.secure.pixiv.net/auth/token",
        data={
            "client_id":      "MOBrBDS8blbauoSck0ZfDbtuzpyT",
            "client_secret":  "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj",
            "code":           code,
            "code_verifier":  code_verifier,
            "grant_type":     "authorization_code",
            "include_policy": "true",
            "redirect_uri":   "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback",
        },
        headers={"User-Agent": "PixivAndroidApp/5.0.234 (Android 11; Pixel 5)"},
    )

    data = res.json()
    if "refresh_token" in data:
        print(f"\n✅ Success!\n\nrefresh_token:\n\n  {data['refresh_token']}\n")
    else:
        print(f"\n❌ Failed (code may have expired, re-run the script):\n{data}")

if __name__ == "__main__":
    main()
    input("\nPress Enter to exit...")
