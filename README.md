# game-manager-bot
Telegram bot to manage games, keeps scores between a group


## How to run

1. **Clone the repository**  
   ```sh
   git clone <repo-url>
   cd game-manager-bot
   ```

2. **Create a virtual environment (Python 3.10+)**  
   ```sh
   python3 -m venv venv
   ```

3. **Activate the virtual environment**  
   - On Linux/macOS:
     ```sh
     source venv/bin/activate
     ```
   - On Windows:
     ```sh
     venv\Scripts\activate
     ```

4. **Install dependencies**  
   ```sh
   pip install -r requirements.txt
   ```

5. **Set your Telegram bot token in a `.env` file**  
   Create a file named `.env` in the project root with this content:
   ```
   BOT_TOKEN=your-telegram-bot-token-here
   ```

6. **Run the bot**  
   ```sh
   python run.py
   ```