import os
import re
import traceback
from datetime import date, datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (ContextTypes, ConversationHandler)

from src.constants import WAITING_FOR_DATE
from src.db import SessionLocal
from src.decorators import reject_if_private_chat
from src.functions import calculate_ranking, generate_rankings_text
from src.handlers.commands import add_me, help_command, show_menu
from src.logging_config import logger
from src.models import Game
from src.utils import with_emoji
from src.templates import HELP_MESSAGE


async def error_handler(
        update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors and log exception details."""
    logger.debug("error_handler() called")
    logger.error("Exception occurred:", exc_info=context.error)

    if isinstance(update, Update) and getattr(update, "message", None):
        await update.message.reply_text(  # type: ignore
            with_emoji(
                ":warning: Something went wrong. "
                "The developers have been notified.")
        )

    traceback_str = ''.join(
        traceback.format_exception(
            None, context.error, context.error.__traceback__  # type: ignore
        )
    )
    logger.debug("Traceback details:\n%s", traceback_str)
    # Notify the developer
    developer_id = os.getenv("DEVELOPER_ID")
    error_message = (
        f"🚨 <b>Error in Game Manager Bot</b>\n"
        f"<b>User:</b> "
        f"{getattr(getattr(update, 'effective_user', None), 'id', 'N/A')}\n"
        f"<b>Chat:</b> "
        f"{getattr(getattr(update, 'effective_chat', None), 'id', 'N/A')}\n"
        f"<b>Error:</b> <code>{context.error}</code>"
    )
    try:
        if developer_id is not None:
            await context.bot.send_message(
                chat_id=int(developer_id),
                text=error_message,
                parse_mode="HTML"
            )
    except Exception as notify_err:
        logger.error("Failed to notify developer: %s", notify_err)
    return


@reject_if_private_chat
async def handle_delete_button(
        update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the button press to delete a game."""
    logger.debug("handle_delete_button() called")
    query = update.callback_query
    if not query or not query.message or not query.data:
        logger.debug("No callback query or message or data found")
        return
    await query.answer()
    chat_id = query.message.chat_id
    game_id = int(query.data.split("_")[2])

    session = SessionLocal()
    game = session.query(Game).filter_by(id=game_id, chat_id=chat_id).first()

    if not game:
        # This is the case when user click on a previous message keyboard
        # to delete a game that is already deleted
        await query.message.reply_text(
            with_emoji(f":x: Game ID {game_id} not found or already deleted."))
        session.close()
        return

    game.deleted_at = datetime.now()  # type: ignore
    session.add(game)
    session.commit()

    if not query.message.text:
        logger.debug("No message text found")
        session.close()
        return

    # Reconstruct the message with strikethrough for deleted game
    # Mark the deleted game with <s> and renumber only non-strikethrough lines
    lines = query.message.text.splitlines()
    new_lines = []
    not_deleted_counter = 1
    # FUTURE: Check if it is better to change the line on the lines
    # list instead of creating a new list
    for line in lines:
        if f"Game ID {game_id}" in line:
            # Remove the number prefix (e.g., "1. ", "2. ") and add strikethrough
            clean_line = re.sub(r'^\d+\.\s*', '', line)
            new_lines.append(f"<s>{clean_line}</s>")
        # If line is previously strikethrough, keep it as is
        elif line.startswith("Game ID"):
            new_lines.append(f"<s>{line}</s>")
        # If line is a game line, renumber it
        elif re.match(r'^\d+\.\s*Game ID', line):
            clean_line = re.sub(r'^\d+\.\s*', '', line)
            new_lines.append(f"{not_deleted_counter}. {clean_line}")
            not_deleted_counter += 1
        else:
            new_lines.append(line)
    message_text = "\n".join(new_lines)

    # Remove the delete button for the deleted game
    if not query.message.reply_markup:
        keyboard = []
    else:
        keyboard = query.message.reply_markup.inline_keyboard
        keyboard = [
            [button for button in row
             if button.callback_data != f"delete_game_{game_id}"]
            for row in keyboard
        ]
        keyboard = [row for row in keyboard if row]

    # Edit the message with HTML parse mode to show strikethrough
    await query.edit_message_text(
        message_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
    )

    session.close()
    return


@reject_if_private_chat
async def handle_menu_rankings(
        update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle rankings menu button press."""
    logger.debug("handle_menu_rankings() called")
    if not update.callback_query:
        return

    await update.callback_query.answer()

    rankings_text = with_emoji(
        ":trophy: <b>Rankings Options</b>\n\n"
        "Choose which rankings you want to view:"
    )

    keyboard = [
        [InlineKeyboardButton(
            text=with_emoji(":calendar: Today"),
            callback_data="rank_today"
        )],
        [InlineKeyboardButton(
            text=with_emoji(":date: Custom Date"),
            callback_data="rank_enter_date"
        )],
        [InlineKeyboardButton(
            text=with_emoji(":chart_with_upwards_trend: All Time"),
            callback_data="rank_all_time"
        )],
        [InlineKeyboardButton(
            text=with_emoji(":left_arrow: Back to Menu"),
            callback_data="menu_back"
        )]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        rankings_text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    return


@reject_if_private_chat
async def handle_rank_callback(
        update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle ranking-related callback queries.

    Handler Assignment:
    - CallbackQueryHandler handles: rank_today, rank_all_time, menu_back (immediate responses)
    - ConversationHandler handles: rank_enter_date (starts conversation), rank_cancel (ends conversation)

    Conversation State Management:
    - rank_enter_date: Start conversation (WAITING_FOR_DATE state)
    - rank_cancel: End conversation (clear any existing state)
    """
    logger.debug("handle_rank_callback() called")
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()

    if query.data == "rank_today":
        # Calculate rankings for today
        await show_rankings_for_date(update, context, datetime.now().date())
    elif query.data == "rank_all_time":
        # Calculate rankings for all time
        await show_rankings_all_time(update, context)
    elif query.data == "rank_enter_date":
        # Ask user to enter a date manually
        await query.edit_message_text(
            with_emoji(
                ":date: <b>Enter Date</b>\n\n"
                "Please enter a date in the format YYYY-MM-DD "
                "(e.g., 2024-01-15):"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    text=with_emoji(":x: Cancel"),
                    callback_data="rank_cancel"
                )
            ]])
        )
        # Set conversation state to wait for date input
        if context.user_data is not None:
            context.user_data['waiting_for_date'] = True
            logger.debug("Setting conversation state to wait for date input")
        return WAITING_FOR_DATE
    elif query.data == "rank_cancel":
        # Cancel date input and go back to rankings menu
        if context.user_data is not None:
            context.user_data.pop('waiting_for_date', None)
        await handle_menu_rankings(update, context)
        return ConversationHandler.END
    elif query.data == "menu_back":
        # Go back to main menu
        await show_menu(update, context)
        # No return needed - handled by CallbackQueryHandler

@reject_if_private_chat
async def handle_date_input(
        update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text message containing date input for rankings."""
    logger.debug("handle_date_input() called")
    if not update.message or not update.message.text:
        return ConversationHandler.END

    # Check if we're waiting for a date input
    if not context.user_data or not context.user_data.get('waiting_for_date'):
        return ConversationHandler.END

    date_text = update.message.text.strip()

    try:
        # Parse the date input
        selected_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        # Clear the waiting state
        if context.user_data:
            context.user_data.pop('waiting_for_date', None)

        # Show rankings for the selected date
        await show_rankings_for_date(update, context, selected_date)

        return ConversationHandler.END

    except ValueError:
        if update.message:
            await update.message.reply_text(
                with_emoji(
                    ":warning: <b>Invalid Date Format</b>\n\n"
                    "Please enter a date in YYYY-MM-DD format "
                    "(e.g., 2024-01-15):"
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        text=with_emoji(":x: Cancel"),
                        callback_data="rank_cancel"
                    )
                ]])
            )
        return WAITING_FOR_DATE

@reject_if_private_chat
async def show_rankings_for_date(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        date: date):
    """Display rankings for a specific date."""
    logger.debug("show_rankings_for_date() called")
    # Calculate rankings
    if update.effective_chat:
        chat_id = update.effective_chat.id
    else:
        return

    session = SessionLocal()
    rankings = calculate_ranking(session, chat_id, date)
    logger.debug(f"Rankings: {rankings}")

    if not rankings:
        rankings_text = with_emoji(
            f":calendar: <b>Rankings for {date.strftime('%Y-%m-%d')}</b>\n\n"
            "No games played on this date in this chat."
        )
    else:
        rankings_text = with_emoji(
            f":calendar: <b>Rankings for {date.strftime('%Y-%m-%d')}</b>\n\n"
        )
        rankings_text += generate_rankings_text(rankings)

    # Add back button
    keyboard = [[
        InlineKeyboardButton(
            text=with_emoji(":left_arrow: Back to Rankings"),
            callback_data="menu_rankings"
        )
    ]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            rankings_text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    elif update.message:
        await update.message.reply_text(
            rankings_text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )

    session.close()
    return

@reject_if_private_chat
async def show_rankings_all_time(
        update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display all-time rankings."""
    logger.debug("show_rankings_all_time() called")
    # Calculate rankings
    if update.effective_chat:
        chat_id = update.effective_chat.id
    else:
        return

    session = SessionLocal()
    rankings = calculate_ranking(session, chat_id)
    logger.debug(f"Rankings: {rankings}")

    if not rankings:
        rankings_text = with_emoji(
            ":no_entry: No games have been played yet in this chat."
        )
    else:
        rankings_text = with_emoji(
            ":chart_with_upwards_trend: <b>All-Time Rankings</b>\n\n"
        )
        rankings_text += generate_rankings_text(rankings)

    # Add back button
    keyboard = [[
        InlineKeyboardButton(
            text=with_emoji(":left_arrow: Back to Rankings"),
            callback_data="menu_rankings"
        )
    ]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            rankings_text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )

    session.close()
    return


# async def handle_menu_start_session(
#         update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Handle start session menu button press."""
#     if not update.callback_query:
#         return

#     await update.callback_query.answer()

#     # Check if a session is already running
#     chat_id = update.effective_chat.id
#     if context.user_data.get(f'session_{chat_id}'):
#         await update.callback_query.edit_message_text(
#             with_emoji(
#                 ":warning: *Session Already Running*\n\n"
#                 "A session is already active in this chat. "
#                 "Please end the current session first."
#             ),
#             parse_mode="MarkdownV2",
#             reply_markup=InlineKeyboardMarkup([[
#                 InlineKeyboardButton(
#                     text=with_emoji(":left_arrow: Back to Menu"),
#                     callback_data="menu_back"
#                 )
#             ]])
#         )
#         return

#     # Initialize session
#     context.user_data[f'session_{chat_id}'] = {
#         'games': [],
#         'message_id': None
#     }

#     # Send initial session message
#     session_text = with_emoji(
#         ":video_game: *Game Session Started*\n\n"
#         "No games played yet.\n\n"
#         "Choose the winner of the first game:"
#     )

#     # Get all players for the winner selection
#     session = SessionLocal()
#     try:
#         players = session.query(Player).all()
#         keyboard = []
#         for player in players:
#             if player and player.first_name:
#                 keyboard.append([InlineKeyboardButton(
#                     text=player.first_name,
#                     callback_data=f"session_winner_{player.id}"
#                 )])

#         # Add cancel button
#         keyboard.append([
#             InlineKeyboardButton(
#                 text=with_emoji(":x: End Session"),
#                 callback_data="session_end"
#             )
#         ])

#         reply_markup = InlineKeyboardMarkup(keyboard)

#         message = await update.callback_query.edit_message_text(
#             session_text,
#             parse_mode="MarkdownV2",
#             reply_markup=reply_markup
#         )

#         # Store message ID for updates
#         context.user_data[f'session_{chat_id}']['message_id'] = message.message_id

#     finally:
#         session.close()


# async def handle_session_winner(
#         update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Handle winner selection in session."""
#     query = update.callback_query
#     if not query or not query.data:
#         return

#     await query.answer()

#     # Extract winner ID
#     winner_id = int(query.data.replace("session_winner_", ""))

#     # Store winner in context
#     chat_id = update.effective_chat.id
#     context.user_data[f'session_{chat_id}']['current_winner'] = winner_id

#     # Get winner name
#     session = SessionLocal()
#     try:
#         winner = session.query(Player).filter_by(id=winner_id).first()
#         if not winner:
#             await query.edit_message_text("Player not found.")
#             return

#         # Update session message to show winner selection
#         session_data = context.user_data[f'session_{chat_id}']
#         games_text = ""
#         if session_data['games']:
#             games_text = "\n\n*Games Played:*\n"
#             for i, game in enumerate(session_data['games'], 1):
#                 games_text += f"{i}\\. {game['winner']} won against {game['loser']}\n"

#         session_text = with_emoji(
#             f":video_game: *Game Session*\n\n"
#             f"Current game: {winner.first_name} won...\n"
#             f"{games_text}\n"
#             f"Choose the loser:"
#         )

#         # Get all players for loser selection (excluding winner)
#         players = session.query(Player).filter(Player.id != winner_id).all()
#         keyboard = []
#         for player in players:
#             if player and player.first_name:
#                 keyboard.append([InlineKeyboardButton(
#                     text=player.first_name,
#                     callback_data=f"session_loser_{player.id}"
#                 )])

#         # Add cancel button
#         keyboard.append([
#             InlineKeyboardButton(
#                 text=with_emoji(":x: Cancel"),
#                 callback_data="session_cancel_game"
#             )
#         ])

#         reply_markup = InlineKeyboardMarkup(keyboard)

#         await query.edit_message_text(
#             session_text,
#             parse_mode="MarkdownV2",
#             reply_markup=reply_markup
#         )

#     finally:
#         session.close()


# async def handle_session_loser(
#         update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Handle loser selection in session."""
#     query = update.callback_query
#     if not query or not query.data:
#         return

#     await query.answer()

#     # Extract loser ID
#     loser_id = int(query.data.replace("session_loser_", ""))

#     # Get session data
#     chat_id = update.effective_chat.id
#     session_data = context.user_data[f'session_{chat_id}']
#     winner_id = session_data.get('current_winner')

#     if not winner_id:
#         await query.edit_message_text("No winner selected.")
#         return

#     # Get player names
#     session = SessionLocal()
#     try:
#         winner = session.query(Player).filter_by(id=winner_id).first()
#         loser = session.query(Player).filter_by(id=loser_id).first()

#         if not winner or not loser:
#             await query.edit_message_text("Player not found.")
#             return

#         if not winner.first_name or not loser.first_name:
#             await query.edit_message_text("Player name not found.")
#             return

#         # Add game to session
#         game = {
#             'winner': winner.first_name,
#             'loser': loser.first_name,
#             'winner_id': winner_id,
#             'loser_id': loser_id
#         }
#         session_data['games'].append(game)

#         # Clear current winner
#         session_data.pop('current_winner', None)

#         # Update session message
#         games_text = ""
#         if session_data['games']:
#             games_text = "\n\n*Games Played:*\n"
#             for i, game in enumerate(session_data['games'], 1):
#                 delete_button = InlineKeyboardButton(
#                     text=with_emoji(":wastebasket:"),
#                     callback_data=f"session_delete_game_{i-1}"
#                 )
#                 games_text += (
#                     f"{i}\\. {game['winner']} won against {game['loser']} "
#                     f"[Delete](callback_data:session_delete_game_{i-1})\n"
#                 )

#         session_text = with_emoji(
#             f":video_game: *Game Session*\n\n"
#             f"Game recorded: {winner.first_name} won against {loser.first_name}\n"
#             f"{games_text}\n"
#             f"Choose the winner of the next game:"
#         )

#         # Get all players for next winner selection
#         players = session.query(Player).all()
#         keyboard = []
#         for player in players:
#             keyboard.append([InlineKeyboardButton(
#                 text=player.first_name,
#                 callback_data=f"session_winner_{player.id}"
#             )])

#         # Add end session button
#         keyboard.append([
#             InlineKeyboardButton(
#                 text=with_emoji(":stop_button: End Session"),
#                 callback_data="session_end"
#             )
#         ])

#         reply_markup = InlineKeyboardMarkup(keyboard)

#         await query.edit_message_text(
#             session_text,
#             parse_mode="MarkdownV2",
#             reply_markup=reply_markup
#         )

#     finally:
#         session.close()


# async def handle_session_delete_game(
#         update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Handle game deletion in session."""
#     query = update.callback_query
#     if not query or not query.data:
#         return

#     await query.answer()

#     # Extract game index
#     game_index = int(query.data.replace("session_delete_game_", ""))

#     # Get session data
#     chat_id = update.effective_chat.id
#     session_data = context.user_data[f'session_{chat_id}']

#     if game_index < len(session_data['games']):
#         # Remove the game
#         deleted_game = session_data['games'].pop(game_index)

#         # Update session message
#         games_text = ""
#         if session_data['games']:
#             games_text = "\n\n*Games Played:*\n"
#             for i, game in enumerate(session_data['games'], 1):
#                 games_text += (
#                     f"{i}\\. {game['winner']} won against {game['loser']}\n"
#                 )

#         session_text = with_emoji(
#             f":video_game: *Game Session*\n\n"
#             f"Game deleted: {deleted_game['winner']} vs {deleted_game['loser']}\n"
#             f"{games_text}\n"
#             f"Choose the winner of the next game:"
#         )

#         # Get all players for next winner selection
#         session = SessionLocal()
#         try:
#             players = session.query(Player).all()
#             keyboard = []
#             for player in players:
#                 keyboard.append([InlineKeyboardButton(
#                     text=player.first_name,
#                     callback_data=f"session_winner_{player.id}"
#                 )])

#             # Add end session button
#             keyboard.append([
#                 InlineKeyboardButton(
#                     text=with_emoji(":stop_button: End Session"),
#                     callback_data="session_end"
#                 )
#             ])

#             reply_markup = InlineKeyboardMarkup(keyboard)

#             await query.edit_message_text(
#                 session_text,
#                 parse_mode="MarkdownV2",
#                 reply_markup=reply_markup
#             )

#         finally:
#             session.close()


# async def handle_session_end(
#         update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Handle session end."""
#     query = update.callback_query
#     if not query:
#         return

#     await query.answer()

#     # Get session data
#     chat_id = update.effective_chat.id
#     session_data = context.user_data.get(f'session_{chat_id}')

#     if not session_data:
#         await query.edit_message_text(
#             with_emoji(":warning: No active session found."),
#             parse_mode="MarkdownV2"
#         )
#         return

#     # Save games to database
#     session = SessionLocal()
#     try:
#         games_saved = 0
#         for game in session_data['games']:
#             new_game = Game(
#                 winner_id=game['winner_id'],
#                 loser_id=game['loser_id'],
#                 date=datetime.now().date(),
#                 chat_id=chat_id
#             )
#             session.add(new_game)
#             games_saved += 1

#         session.commit()

#         # Show final summary
#         games_text = ""
#         if session_data['games']:
#             games_text = "\n\n*Games Played:*\n"
#             for i, game in enumerate(session_data['games'], 1):
#                 games_text += (
#                     f"{i}\\. {game['winner']} won against {game['loser']}\n"
#                 )

#         summary_text = with_emoji(
#             f":stop_button: *Session Ended*\n\n"
#             f"Total games: {len(session_data['games'])}\n"
#             f"Games saved: {games_saved}\n"
#             f"{games_text}"
#         )

#         # Clear session data
#         if context.user_data:
#             context.user_data.pop(f'session_{chat_id}', None)

#         await query.edit_message_text(
#             summary_text,
#             parse_mode="MarkdownV2",
#             reply_markup=InlineKeyboardMarkup([[
#                 InlineKeyboardButton(
#                     text=with_emoji(":left_arrow: Back to Menu"),
#                     callback_data="menu_back"
#                 )
#             ]])
#         )

#     except Exception as e:
#         session.rollback()
#         logger.error(f"Error saving session games: {e}")
#         await query.edit_message_text(
#             with_emoji(":warning: Error saving games to database."),
#             parse_mode="MarkdownV2"
#         )
#     finally:
#         session.close()


# async def handle_session_cancel_game(
#         update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Handle game cancellation in session."""
#     query = update.callback_query
#     if not query:
#         return

#     await query.answer()

#     # Clear current winner and go back to winner selection
#     chat_id = update.effective_chat.id
#     session_data = context.user_data[f'session_{chat_id}']
#     if session_data:
#         session_data.pop('current_winner', None)

#     # Update session message
#     games_text = ""
#     if session_data['games']:
#         games_text = "\n\n*Games Played:*\n"
#         for i, game in enumerate(session_data['games'], 1):
#             games_text += f"{i}\\. {game['winner']} won against {game['loser']}\n"

#     session_text = with_emoji(
#         f":video_game: *Game Session*\n\n"
#         f"Game cancelled.\n"
#         f"{games_text}\n"
#         f"Choose the winner of the next game:"
#     )

#     # Get all players for winner selection
#     session = SessionLocal()
#     try:
#         players = session.query(Player).all()
#         keyboard = []
#         for player in players:
#             if player and player.first_name:
#                 keyboard.append([InlineKeyboardButton(
#                     text=player.first_name,
#                     callback_data=f"session_winner_{player.id}"
#                 )])

#         # Add end session button
#         keyboard.append([
#             InlineKeyboardButton(
#                 text=with_emoji(":stop_button: End Session"),
#                 callback_data="session_end"
#             )
#         ])

#         reply_markup = InlineKeyboardMarkup(keyboard)

#         await query.edit_message_text(
#             session_text,
#             parse_mode="MarkdownV2",
#             reply_markup=reply_markup
#         )

#     finally:
#         session.close()


# async def handle_menu_end_session(
#         update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Handle end session menu button press."""
#     if not update.callback_query:
#         return

#     await update.callback_query.answer()

#     # Check if a session is running
#     chat_id = update.effective_chat.id
#     session_data = context.user_data.get(f'session_{chat_id}')

#     if not session_data:
#         await update.callback_query.edit_message_text(
#             with_emoji(
#                 ":warning: *No Active Session*\n\n"
#                 "There is no session running in this chat."
#             ),
#             parse_mode="MarkdownV2",
#             reply_markup=InlineKeyboardMarkup([[
#                 InlineKeyboardButton(
#                     text=with_emoji(":left_arrow: Back to Menu"),
#                     callback_data="menu_back"
#                 )
#             ]])
#         )
#         return

#     # Show session summary without buttons
#     games_text = ""
#     if session_data['games']:
#         games_text = "\n\n*Games Played:*\n"
#         for i, game in enumerate(session_data['games'], 1):
#             games_text += f"{i}\\. {game['winner']} won against {game['loser']}\n"

#     summary_text = with_emoji(
#         f":stop_button: *Session Summary*\n\n"
#         f"Total games: {len(session_data['games'])}\n"
#         f"{games_text}\n"
#         f"Session is still active. Use the session controls to end it."
#     )

#     await update.callback_query.edit_message_text(
#         summary_text,
#         parse_mode="MarkdownV2",
#         reply_markup=InlineKeyboardMarkup([[
#             InlineKeyboardButton(
#                 text=with_emoji(":left_arrow: Back to Menu"),
#                 callback_data="menu_back"
#             )
#         ]])
#     )


@reject_if_private_chat
async def handle_menu_add_me(
        update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle add me menu button press."""
    logger.debug("handle_menu_add_me() called")
    if not update.callback_query:
        logger.debug("No callback query found")
        return

    await update.callback_query.answer()

    # Call the existing add_me function
    await add_me(update, context)

    # Show success message and back button
    await update.callback_query.edit_message_text(
        with_emoji(
            "<b>:white_check_mark: Registration Complete</b>\n\n"
            "Your information has been added/updated successfully!"
        ),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                text=with_emoji(":left_arrow: Back to Menu"),
                callback_data="menu_back"
            )
        ]])
    )
    return

@reject_if_private_chat
async def handle_menu_help(
        update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle help menu button press."""
    logger.debug("handle_menu_help() called")
    if not update.callback_query:
        logger.debug("No callback query found")
        return
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        with_emoji(HELP_MESSAGE),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                text=with_emoji(":left_arrow: Back to Menu"),
                callback_data="menu_back"
            )
        ]])
    )
    return


@reject_if_private_chat
async def handle_menu_callback(
        update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all menu-related callback queries."""
    logger.debug("handle_menu_callback() called")
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()

    if query.data == "menu_rankings":
        await handle_menu_rankings(update, context)
    # elif query.data == "menu_start_session":
    #     await handle_menu_start_session(update, context)
    # elif query.data == "menu_end_session":
    #     await handle_menu_end_session(update, context)
    elif query.data == "menu_add_me":
        logger.debug("menu_add_me callback received")
        await handle_menu_add_me(update, context)
    elif query.data == "menu_back":
        logger.debug("menu_back callback received")
        await show_menu(update, context)
    elif query.data == "menu_help":
        logger.debug("menu_help callback received")
        await handle_menu_help(update, context)
    return
