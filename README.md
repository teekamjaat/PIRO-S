# Telegram Premium Bot

A Koyeb-ready Telegram premium-plan bot with:

- Premium plans
- Separate payment image for each plan
- Screenshot-based manual payment verification
- Admin approve/reject buttons
- MongoDB user and payment storage
- Premium expiry
- Profile
- Support button
- Koyeb health server

## 1. Create the bot

Create a bot with BotFather and copy the bot token.

## 2. MongoDB

Create a MongoDB database and copy the connection URI.

## 3. Configure environment variables

Copy `.env.example` values into Koyeb environment variables.

Required:

- `BOT_TOKEN`
- `ADMIN_IDS`
- `MONGODB_URI`

Optional:

- `MONGODB_DB`
- `START_IMAGE_FILE_ID`
- `SUPPORT_URL`
- `WEEKLY_IMAGE_FILE_ID`
- `QUARTERLY_IMAGE_FILE_ID`
- `MONTHLY_IMAGE_FILE_ID`
- `PERMANENT_IMAGE_FILE_ID`

## 4. Get Telegram image file IDs

Send your start image and each plan's payment/QR image to the bot.

Use Telegram file IDs in the environment variables. File IDs are preferable to downloading and storing images in the repository.

## 5. Run locally

```bash
pip install -r requirements.txt
python bot.py
```

## 6. Koyeb

Use the GitHub repository as the deployment source.

Build command:

```bash
pip install -r requirements.txt
```

Run command:

```bash
python bot.py
```

The bot also starts an HTTP health server on the Koyeb `PORT` environment variable.

## Payment verification

The user:

1. Selects a plan.
2. Opens the payment page.
3. Clicks `Verify Payment`.
4. Sends a payment screenshot.

The bot forwards the screenshot to the configured admin IDs.

Admin chooses:

- `Approve` → premium is activated.
- `Reject` → payment is rejected.

Do not put your Bot Token or MongoDB password into GitHub.
