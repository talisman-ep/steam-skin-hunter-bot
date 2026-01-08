# 🔫 Steam Skin Hunter Bot

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Aiogram](https://img.shields.io/badge/Aiogram-3.x-blueviolet)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)
![License](https://img.shields.io/badge/License-MIT-green)

**Steam Skin Hunter** is an asynchronous Telegram bot designed to track Counter-Strike 2 (CS2) skin prices on the Steam Community Market in real-time. It helps traders and gamers monitor price drops and evaluate their inventory value instantly.

> **Key Feature:** The bot implements a smart "Anti-Ban" algorithm to handle Steam's aggressive Rate Limiting (HTTP 429), ensuring stable operation 24/7.

## 🚀 Features

- **🔎 Smart Search:** Instantly find the lowest price for any CS2 skin via Steam API.
- **📈 Price Monitoring:** Tracks added skins in the background and records price history in PostgreSQL.
- **🎒 Inventory Scanner:** Parses public Steam inventories (even with 1000+ items), calculates total value in USD and UAH.
- **🛡️ Anti-Rate Limit System:** Automatically detects Steam bans (429 Too Many Requests), pauses requests, and retries with exponential backoff.
- **🇺🇦 Multi-currency:** Automatic conversion from USD to UAH (Ukrainian Hryvnia).

## 🛠️ Tech Stack

- **Language:** Python 3.10+
- **Bot Framework:** [Aiogram 3.x](https://docs.aiogram.dev/) (Asynchronous)
- **HTTP Client:** [Aiohttp](https://docs.aiohttp.org/) (High-performance async requests)
- **Database:** PostgreSQL + [Asyncpg](https://github.com/MagicStack/asyncpg) driver
- **Architecture:** Modular design (Separation of concerns: Bot / Scraper / Database).

## 📂 Project Structure

```text
steam-skin-hunter-bot/
├── bot.py             # Telegram bot interface (Handlers & Keyboards)
├── tasks.py           # Background monitoring logic (Cron-like tasks)
├── steam_client.py    # Custom wrapper for Steam Market/Inventory API
├── database.py        # Async PostgreSQL connection pool & queries
├── main.py            # Entry point (Runs Bot + Tasks concurrently)
├── config.py          # Configuration (Tokens & Secrets) - *Gitignored*
└── requirements.txt   # Project dependencies

```

## ⚙️ Installation & Setup

1. **Clone the repository**
```bash
git clone [https://github.com/your-username/steam-skin-hunter-bot.git](https://github.com/your-username/steam-skin-hunter-bot.git)
cd steam-skin-hunter-bot

```


2. **Create a virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

```


3. **Install dependencies**
```bash
pip install -r requirements.txt

```


4. **Database Setup**
* Install PostgreSQL.
* Create a database named `steam_skins_db`.
* The bot will automatically connect (ensure credentials in config are correct).
* *Note: You might need to create tables `skin_prices` and `tracked_items` manually using SQL.*


5. **Configuration**
* Rename `config_example.py` to `config.py`.
* Open `config.py` and insert your:
* Telegram Bot Token (from @BotFather)
* Database credentials
* Steam settings




6. **Run the System**
```bash
python main.py

```



## 📸 Screenshots

<img width="652" height="379" alt="image" src="https://github.com/user-attachments/assets/189debd7-8976-4235-83da-fd33ee15632f" />

<img width="657" height="163" alt="image" src="https://github.com/user-attachments/assets/5ee67300-366c-4311-8a41-84f47821325e" />

<img width="637" height="196" alt="image" src="https://github.com/user-attachments/assets/ebfdc2c5-5f67-4060-9832-7bbc04f21c2d" />


## 🔮 Future Roadmap

* [ ] **Profit Calculator:** Track purchase price vs current price.
* [ ] **Price Charts:** Generate visual graphs (Matplotlib) for price history.
* [ ] **Docker Support:** Containerize the application for easier deploy.
* [ ] **Web Dashboard:** Simple frontend to view stats.

## 🤝 Contributing

Contributions are welcome! Please fork the repository and create a pull request.
