# How to Generate a Personal Access Token (PAT) on GitHub

Since you have 2-Factor Authentication (2FA) enabled, you cannot use your account password when pushing code from the command line. You must use a Personal Access Token.

## Steps to Generate a Token

1.  **Log in** to your GitHub account.
2.  Click your **profile photo** in the top-right corner and select **Settings**.
3.  In the left sidebar, scroll all the way down and click **Developer settings**.
4.  In the left sidebar, click **Personal access tokens** -> **Tokens (classic)**.
5.  Click the **Generate new token** button and select **Generate new token (classic)**.
6.  **Note/Name**: Give it a name like "Laptop CLI" so you remember what it's for.
7.  **Expiration**: Choose "No expiration" (easiest for personal projects) or set a custom days limit.
8.  **Select Scopes** (Permissions):
    *   [x] **repo** (Full control of private repositories) - *Check this entire box*
    *   [x] **workflow** (Check this if you plan to use GitHub Actions)
9.  Scroll to the bottom and click **Generate token**.

## IMPORTANT
**Copy the token immediately!** You will not be able to see it again after you leave that page.

---

## How to Use It
When you run the push script and it asks for a **Password** for `https://github.com`:
**Paste this Token instead of your password.**
