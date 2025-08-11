# Game Manager Bot - Test Scenarios

## Overview
This document contains comprehensive test scenarios for the Telegram Game Manager Bot. The bot manages games, tracks player scores, and maintains rankings in group chats.

## Test Environment Setup
- Create a test Telegram group
- Add the bot to the group
- Ensure bot has necessary permissions (send messages, read messages)
- Set up test users with different usernames and first names

---

## 1. Player Registration Tests

### 1.1 Basic Player Registration
**Scenario**: New player registers for the first time
- **Command**: `/add_me`
- **Expected Result**: 
  - Player added to database
  - Success message: "You have been added as a player! You can now use the /played command to record your games."
  - Player info (telegram_id, username, first_name) stored correctly

### 1.2 Duplicate Player Registration
**Scenario**: Player tries to register again
- **Command**: `/add_me` (same user)
- **Expected Result**: 
  - Error message: "You are already in the database."
  - No duplicate entries created

### 1.3 Player Info Update
**Scenario**: Player changes username/first_name and re-registers
- **Command**: `/add_me` (after changing profile info)
- **Expected Result**: 
  - Success message: "Your information has been updated!"
  - Database updated with new info

### 1.4 Private Chat Registration Attempt
**Scenario**: User tries to register in private chat with bot
- **Command**: `/add_me` (in private chat)
- **Expected Result**: 
  - Command rejected
  - No response or error message indicating private chat not allowed

---

## 2. Game Recording Tests

### 2.1 Basic Game Recording
**Scenario**: Record a simple game between two registered players
- **Command**: `/played @winner @loser`
- **Expected Result**: 
  - Game recorded successfully
  - Success message with game ID
  - Delete button provided for the game
  - Date defaults to current date (Asia/Tehran timezone)

### 2.2 Multiple Games Recording
**Scenario**: Record multiple games in one command
- **Command**: `/played @winner1 @loser1 @winner2 @loser2 @winner3 @loser3`
- **Expected Result**: 
  - All games recorded successfully
  - Success message listing all games with IDs
  - Delete buttons for each game

### 2.3 Game Recording with Custom Date
**Scenario**: Record game with specific date
- **Command**: `/played @winner @loser date=2024-01-15`
- **Expected Result**: 
  - Game recorded with specified date
  - Success message shows correct date

### 2.4 Invalid Date Format
**Scenario**: Use wrong date format
- **Command**: `/played @winner @loser date=15-01-2024`
- **Expected Result**: 
  - Error message: "Invalid date format. Use date=YYYY-MM-DD."
  - No game recorded

### 2.5 Invalid Date Value
**Scenario**: Use invalid date values
- **Commands**: 
  - `/played @winner @loser date=2024-13-01` (invalid month)
  - `/played @winner @loser date=2024-02-30` (invalid day)
  - `/played @winner @loser date=2024-00-01` (zero month)
- **Expected Result**: 
  - Error message or validation failure
  - No game recorded

### 2.6 Unregistered Player Attempt
**Scenario**: Try to record game with unregistered player
- **Command**: `/played @unregistered_user @registered_user`
- **Expected Result**: 
  - Error message: "Player @unregistered_user not found. Ask them to send /add_me first."
  - No game recorded

### 2.7 Self-Play Game Attempt
**Scenario**: Try to record game where winner and loser are same person
- **Command**: `/played @same_user @same_user`
- **Expected Result**: 
  - Error message: "Winner and loser cannot be the same person: [username] Try again."
  - No game recorded

### 2.8 Odd Number of Players
**Scenario**: Provide odd number of players
- **Command**: `/played @player1 @player2 @player3`
- **Expected Result**: 
  - Error message: "Please provide an even number of players (@winner @loser\n@winner @loser\n.\n.)."
  - No games recorded

### 2.9 Insufficient Mentions
**Scenario**: Provide less than 2 mentions
- **Command**: `/played @player1`
- **Expected Result**: 
  - Error message: "Please provide 2 mentions or text mentions in the message."
  - No game recorded

### 2.10 Private Chat Game Recording
**Scenario**: Try to record game in private chat
- **Command**: `/played @winner @loser` (in private chat)
- **Expected Result**: 
  - Command rejected
  - No response or error message

---

## 3. Game Deletion Tests

### 3.1 Delete Single Game
**Scenario**: Delete a game using the delete button
- **Action**: Click "🗑️ Delete Game [ID]" button
- **Expected Result**: 
  - Game deleted from database
  - Message updated to show deleted game as strikethrough
  - Delete button removed from keyboard

### 3.2 Delete Game from Different Chat
**Scenario**: Try to delete game from different chat than where it was created
- **Action**: Copy delete button callback to different chat
- **Expected Result**: 
  - Error message: "Game not found."
  - Game remains in database

### 3.3 Delete Non-existent Game
**Scenario**: Try to delete game that doesn't exist
- **Action**: Use invalid game ID in delete callback
- **Expected Result**: 
  - Error message: "Game not found."
  - No database changes

---

## 4. Ranking Tests

### 4.1 Basic Ranking Display
**Scenario**: View rankings for current chat
- **Command**: `/rank`
- **Expected Result**: 
  - Rankings displayed with win ratios
  - Players sorted by win ratio (highest first)
  - Medal emojis for top 3 players
  - Message: "🏆 All-Time Champions Are Here! ✨"

### 4.2 Today's Rankings
**Scenario**: View rankings for today only
- **Command**: `/rank today`
- **Expected Result**: 
  - Only today's games included in calculations
  - Message: "🏆 [date] Champions Are Here! ✨"

### 4.3 Custom Date Rankings
**Scenario**: View rankings for specific date
- **Command**: `/rank 2024-01-15`
- **Expected Result**: 
  - Only games from 2024-01-15 included
  - Message: "🏆 2024-01-15 Champions Are Here! ✨"

### 4.4 Invalid Date Format in Ranking
**Scenario**: Use wrong date format in ranking command
- **Command**: `/rank 15-01-2024`
- **Expected Result**: 
  - Error message: "Invalid date format. Use YYYY-MM-DD or 'today'."

### 4.5 No Games Ranking
**Scenario**: View rankings when no games exist
- **Command**: `/rank` (in chat with no games)
- **Expected Result**: 
  - Message: "🚫 No games played yet in this chat."

### 4.6 Ranking with Win Ratio Calculation
**Scenario**: Verify win ratio calculations
- **Setup**: Create games where player A wins 3, loses 1
- **Command**: `/rank`
- **Expected Result**: 
  - Player A shows 75% win ratio
  - Correct ranking order

---

## 5. Menu System Tests

### 5.1 Main Menu Display
**Scenario**: Display main menu
- **Command**: `/menu`
- **Expected Result**: 
  - Menu with buttons: Rankings, Add Me, Help
  - Proper emoji formatting

### 5.2 Menu Rankings Button
**Scenario**: Access rankings through menu
- **Action**: Click "🏆 Rankings" button
- **Expected Result**: 
  - Rankings options menu displayed
  - Options: Today, Custom Date, All Time, Back to Menu

### 5.3 Menu Add Me Button
**Scenario**: Access add me through menu
- **Action**: Click "👤 Add Me" button
- **Expected Result**: 
  - Same as `/add_me` command
  - Player registration process

### 5.4 Menu Help Button
**Scenario**: Access help through menu
- **Action**: Click "❓ Help" button
- **Expected Result**: 
  - Help message displayed
  - Same as `/help` command

### 5.5 Back to Menu Navigation
**Scenario**: Navigate back to main menu
- **Action**: Click "⬅️ Back to Menu" button
- **Expected Result**: 
  - Returns to main menu
  - All menu options available

---

## 6. Games History Tests

### 6.1 View Today's Games
**Scenario**: View games played today
- **Command**: `/games`
- **Expected Result**: 
  - List of today's games
  - Delete buttons for each game
  - Proper formatting with game IDs

### 6.2 View Games for Specific Date
**Scenario**: View games for specific date
- **Command**: `/games date=2024-01-15`
- **Expected Result**: 
  - List of games from 2024-01-15
  - Delete buttons for each game

### 6.3 Invalid Date Format in Games
**Scenario**: Use wrong date format in games command
- **Command**: `/games date=15-01-2024`
- **Expected Result**: 
  - Error message: "Invalid date format. Use date=YYYY-MM-DD."

### 6.4 No Games for Date
**Scenario**: View games for date with no games
- **Command**: `/games date=2024-01-01` (assuming no games on this date)
- **Expected Result**: 
  - Message: "🚫 No games played on this date in this chat."

---

## 7. Error Handling Tests

### 7.1 Database Connection Error
**Scenario**: Simulate database connection failure
- **Setup**: Stop database service
- **Action**: Try any command that requires database
- **Expected Result**: 
  - Error handled gracefully
  - User notified of issue
  - Developer notified (if DEVELOPER_ID set)

### 7.2 Invalid Callback Data
**Scenario**: Send invalid callback data
- **Action**: Send malformed callback query
- **Expected Result**: 
  - Error handled gracefully
  - No crash or unexpected behavior

### 7.3 Missing Message Context
**Scenario**: Handle missing message context
- **Action**: Send update without message
- **Expected Result**: 
  - Graceful handling
  - No errors or crashes

---

## 8. Edge Cases and Boundary Tests

### 8.1 Very Long Usernames
**Scenario**: Test with very long username
- **Setup**: Create user with 100+ character username
- **Action**: Register and record games
- **Expected Result**: 
  - Handled properly
  - No database issues

### 8.2 Special Characters in Names
**Scenario**: Test with special characters
- **Setup**: Create user with emojis, unicode characters in name
- **Action**: Register and record games
- **Expected Result**: 
  - Properly stored and displayed
  - No encoding issues

### 8.3 Multiple Games Same Players Same Day
**Scenario**: Record multiple games between same players on same day
- **Command**: `/played @player1 @player2 @player1 @player2`
- **Expected Result**: 
  - All games recorded
  - Proper win/loss tracking

### 8.4 Games Across Different Chats
**Scenario**: Record games in different chats
- **Setup**: Add bot to multiple groups
- **Action**: Record games in each chat
- **Expected Result**: 
  - Games isolated by chat_id
  - Rankings separate per chat

### 8.5 Timezone Edge Cases
**Scenario**: Test timezone handling
- **Setup**: Record games around midnight (Asia/Tehran timezone)
- **Action**: Check date assignment
- **Expected Result**: 
  - Correct date based on Asia/Tehran timezone
  - Consistent date handling

---

## 9. Performance Tests

### 9.1 Large Number of Games
**Scenario**: Test with many games
- **Setup**: Create 100+ games
- **Action**: View rankings and games history
- **Expected Result**: 
  - Reasonable response time
  - No timeout issues

### 9.2 Many Players
**Scenario**: Test with many players
- **Setup**: Register 50+ players
- **Action**: View rankings
- **Expected Result**: 
  - Rankings calculated correctly
  - Reasonable display time

### 9.3 Concurrent Operations
**Scenario**: Test concurrent game recordings
- **Action**: Multiple users record games simultaneously
- **Expected Result**: 
  - No race conditions
  - All games recorded correctly

---

## 10. Security Tests

### 10.1 Unauthorized Game Deletion
**Scenario**: Try to delete game from different user
- **Action**: Use delete callback from different chat/user
- **Expected Result**: 
  - Deletion prevented
  - Proper error message

### 10.2 SQL Injection Attempts
**Scenario**: Test for SQL injection vulnerabilities
- **Action**: Use malicious input in commands
- **Expected Result**: 
  - Input properly sanitized
  - No SQL injection possible

### 10.3 XSS Prevention
**Scenario**: Test for XSS vulnerabilities
- **Action**: Use HTML/script tags in names
- **Expected Result**: 
  - Content properly escaped
  - No script execution

---

## Test Execution Checklist

### Pre-test Setup
- [ ] Bot deployed and running
- [ ] Test group created
- [ ] Bot added to group with proper permissions
- [ ] Test users available with different usernames
- [ ] Database accessible and empty (for clean testing)
- [ ] Logs enabled for debugging

### Test Execution
- [ ] Run all player registration tests
- [ ] Run all game recording tests
- [ ] Run all deletion tests
- [ ] Run all ranking tests
- [ ] Run all menu system tests
- [ ] Run all games history tests
- [ ] Run all error handling tests
- [ ] Run all edge case tests
- [ ] Run all performance tests
- [ ] Run all security tests

### Post-test Verification
- [ ] Check database integrity
- [ ] Verify all expected data present
- [ ] Check logs for errors
- [ ] Verify bot still responsive
- [ ] Clean up test data if needed

---

## Notes
- All tests should be run in a test environment, not production
- Some tests may require manual intervention (like clicking buttons)
- Timezone-dependent tests should account for Asia/Tehran timezone
- Database should be backed up before running destructive tests
- Consider using automated testing tools for repetitive scenarios 