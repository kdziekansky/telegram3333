from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.ui_elements import credit_status_bar, info_card, section_divider, feature_badge, progress_bar
from utils.message_formatter_enhanced import format_credit_info, format_transaction_report
from utils.visual_styles import style_message, create_header, create_section, create_status_indicator
from utils.tips import get_random_tip, should_show_tip
from utils.credit_warnings import get_low_credits_notification, get_credit_recommendation
from config import BOT_NAME
from utils.menu_manager import update_menu_message, store_menu_state
from utils.user_utils import get_user_language
from utils.translations import get_text
from database.credits_client import (
    get_user_credits, add_user_credits, deduct_user_credits, 
    get_credit_packages, get_package_by_id, purchase_credits,
    get_user_credit_stats
)
from utils.credit_analytics import (
    generate_credit_usage_chart, generate_usage_breakdown_chart, 
    get_credit_usage_breakdown, predict_credit_depletion
)
import matplotlib
matplotlib.use('Agg')  # Required for operation without a graphical interface

from database.credits_client import add_stars_payment_option, get_stars_conversion_rate

async def credits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /credits command with enhanced visual presentation
    Display information about user's credits
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    credits = get_user_credits(user_id)
    
    # Przygotuj podstawową informację bez zależności od innych funkcji, które mogą powodować błędy
    message = f"*Stan kredytów*\n\n"
    message += f"Dostępne kredyty: *{credits}*\n\n"
    
    # Pobierz statystyki kredytów (zabezpieczone przed błędami)
    try:
        from database.credits_client import get_user_credit_stats
        stats = get_user_credit_stats(user_id)
        
        if stats:
            message += f"*Statystyki:*\n"
            message += f"▪️ Łącznie zakupiono: {stats.get('total_purchased', 0)} kredytów\n"
            message += f"▪️ Średnie dzienne zużycie: {int(stats.get('avg_daily_usage', 0))} kredytów\n"
            
            if stats.get('most_expensive_operation'):
                message += f"▪️ Najdroższa operacja: {stats.get('most_expensive_operation')}\n"
    except Exception as e:
        print(f"Błąd przy pobieraniu statystyk: {e}")
    
    # Dodaj informację o kosztach operacji
    message += f"\n*Koszty operacji:*\n"
    message += f"▪️ Wiadomość standardowa (GPT-3.5): 1 kredyt\n"
    message += f"▪️ Wiadomość premium (GPT-4o): 3 kredyty\n"
    message += f"▪️ Wiadomość ekspercka (GPT-4): 5 kredytów\n"
    message += f"▪️ Generowanie obrazu: 10-15 kredytów\n"
    message += f"▪️ Analiza dokumentu: 5 kredytów\n"
    message += f"▪️ Analiza zdjęcia: 8 kredytów\n\n"
    
    # Stwórz przyciski
    keyboard = [
        [InlineKeyboardButton("💳 Kup kredyty", callback_data="menu_credits_buy")],
        [
            InlineKeyboardButton("💰 Metody płatności", callback_data="payment_command"),
            InlineKeyboardButton("🔄 Subskrypcje", callback_data="subscription_command")
        ],
        [InlineKeyboardButton("📜 Historia transakcji", callback_data="transactions_command")],
        [InlineKeyboardButton("⬅️ Powrót", callback_data="menu_back_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Błąd przy wysyłaniu wiadomości z kredytami: {e}")
        # Fallback bez formatowania
        await update.message.reply_text(
            message.replace("*", ""),
            reply_markup=reply_markup
        )

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /buy command with enhanced visual presentation
    Directs users to payment options
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Create styled header for payment options
    message = create_header("Zakup kredytów", "credits")
    
    # Add descriptive text with visual formatting
    message += (
        "Wybierz jedną z dostępnych metod płatności, aby kupić pakiet kredytów. "
        "Kredyty są używane do wszystkich operacji w bocie, takich jak:\n\n"
        "▪️ Rozmowy z różnymi modelami AI\n"
        "▪️ Generowanie obrazów\n"
        "▪️ Analizowanie dokumentów i zdjęć\n"
        "▪️ Tłumaczenie tekstów\n\n"
        "Dostępne są różne metody płatności."
    )
    
    # Add section about subscription benefits
    message += "\n\n" + create_section("Korzyści z subskrypcji", 
        "▪️ Automatyczne odnowienie kredytów co miesiąc\n"
        "▪️ Niższy koszt kredytów\n"
        "▪️ Priorytetowa obsługa\n"
        "▪️ Dodatkowe funkcje premium")
    
    # Create enhanced buttons for payment options - usunięto opcję gwiazdek Telegram
    keyboard = [
        [
            InlineKeyboardButton("💳 " + get_text("credit_card", language, default="Karta płatnicza"), callback_data="payment_method_stripe"),
            InlineKeyboardButton("🔄 " + get_text("subscription", language, default="Subskrypcja"), callback_data="payment_method_stripe_subscription")
        ],
        [
            InlineKeyboardButton("⬅️ " + get_text("back", language, default="Powrót"), callback_data="menu_back_main")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def handle_credit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle buttons related to credits
    """
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    await query.answer()
    
    # Handle credits purchase options - ZMODYFIKOWANE
    if query.data == "menu_credits_buy" or query.data == "credits_buy" or query.data == "Kup":
        try:
            # Importuj funkcję buy_command
            from handlers.credit_handler import buy_command
            
            # Utwórz sztuczny obiekt update
            fake_update = type('obj', (object,), {
                'effective_user': query.from_user,
                'message': query.message,
                'effective_chat': query.message.chat
            })
            
            # Usuń oryginalną wiadomość z menu
            try:
                await query.message.delete()
            except Exception as e:
                print(f"Nie można usunąć wiadomości: {e}")
            
            # Wywołaj nowy interfejs zakupów (/buy)
            await buy_command(fake_update, context)
            return True
            
        except Exception as e:
            print(f"Błąd przy przekierowaniu do zakupu kredytów: {e}")
            import traceback
            traceback.print_exc()
            
            # W przypadku błędu, wyświetl komunikat
            try:
                keyboard = [[InlineKeyboardButton("⬅️ Menu główne", callback_data="menu_back_main")]]
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="Wystąpił błąd. Spróbuj użyć komendy /buy",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e2:
                print(f"Błąd przy wyświetlaniu komunikatu: {e2}")
            return True
    
    # Handle credit purchase options - ZMODYFIKOWANE
    if query.data == "credits_buy" or query.data == "menu_credits_buy" or query.data == "Kup":
        try:
            # Importuj funkcję buy_command
            from handlers.credit_handler import buy_command
            
            # Utwórz sztuczny obiekt update
            fake_update = type('obj', (object,), {
                'effective_user': query.from_user,
                'message': query.message,
                'effective_chat': query.message.chat
            })
            
            # Usuń oryginalną wiadomość z menu
            await query.message.delete()
            
            # Wywołaj nowy interfejs zakupów (/buy)
            await buy_command(fake_update, context)
            return True
            
        except Exception as e:
            print(f"Błąd przy przekierowaniu do zakupu kredytów: {e}")
            import traceback
            traceback.print_exc()
            
            # W przypadku błędu, wyświetl komunikat
            try:
                keyboard = [[InlineKeyboardButton("⬅️ Menu główne", callback_data="menu_back_main")]]
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="Wystąpił błąd. Spróbuj użyć komendy /buy",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e2:
                print(f"Błąd przy wyświetlaniu komunikatu: {e2}")
            return True
    
    # Handle advanced credit analytics
    if query.data == "credits_stats" or query.data == "credit_advanced_analytics":
        user_id = query.from_user.id
        language = get_user_language(context, user_id)
        
        # Inform user that analysis is starting
        if hasattr(query.message, 'caption'):
            await query.edit_message_caption(
                caption="⏳ Analyzing credit usage data..."
            )
        else:
            await query.edit_message_text(
                text="⏳ Analyzing credit usage data..."
            )
        
        # Default number of days for analysis
        days = 30
        
        # Get credit depletion forecast
        depletion_info = predict_credit_depletion(user_id, days)
        
        if not depletion_info:
            if hasattr(query.message, 'caption'):
                await query.edit_message_caption(
                    caption="You don't have enough credit usage history to perform analysis. Try again after performing several operations."
                )
            else:
                await query.edit_message_text(
                    text="You don't have enough credit usage history to perform analysis. Try again after performing several operations."
                )
            return True
        
        # Prepare analysis message
        message = f"📊 *{get_text('credit_analytics', language, default='Analiza wykorzystania kredytów')}*\n\n"
        message += f"{get_text('current_balance', language)}: *{depletion_info['current_balance']}* {get_text('credits', language)}\n"
        message += f"{get_text('average_daily_usage', language, default='Średnie dzienne zużycie')}: *{depletion_info['average_daily_usage']}* {get_text('credits', language)}\n"
        
        if depletion_info['days_left']:
            message += f"{get_text('predicted_depletion', language, default='Przewidywane wyczerpanie kredytów')}: {get_text('in_days', language, default='za')} *{depletion_info['days_left']}* {get_text('days', language, default='dni')} "
            message += f"({depletion_info['depletion_date']})\n\n"
        else:
            message += f"{get_text('not_enough_data', language, default='Za mało danych, aby przewidzieć wyczerpanie kredytów.')}.\n\n"
        
        # Get credit usage breakdown
        usage_breakdown = get_credit_usage_breakdown(user_id, days)
        
        if usage_breakdown:
            message += f"*{get_text('usage_breakdown', language, default='Rozkład zużycia kredytów')}:*\n"
            for category, amount in usage_breakdown.items():
                percentage = amount / sum(usage_breakdown.values()) * 100
                message += f"- {category}: *{amount}* {get_text('credits', language)} ({percentage:.1f}%)\n"
        
        # Update message with analysis
        if hasattr(query.message, 'caption'):
            await query.edit_message_caption(
                caption=message,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text(
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Generate and send charts
        # Usage history chart
        usage_chart = generate_credit_usage_chart(user_id, days)
        if usage_chart:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=usage_chart,
                caption=f"📈 {get_text('usage_history_chart', language, default=f'Historia wykorzystania kredytów z ostatnich {days} dni')}"
            )
        
        # Usage breakdown chart
        breakdown_chart = generate_usage_breakdown_chart(user_id, days)
        if breakdown_chart:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=breakdown_chart,
                caption=f"📊 {get_text('usage_breakdown_chart', language, default=f'Rozkład wykorzystania kredytów z ostatnich {days} dni')}"
            )
        
        # Add back button
        keyboard = [[InlineKeyboardButton(get_text("back", language), callback_data="menu_credits_check")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Update message with back button
        try:
            if hasattr(query.message, 'caption'):
                await query.edit_message_reply_markup(reply_markup=reply_markup)
            else:
                await query.message.edit_reply_markup(reply_markup=reply_markup)
        except Exception as e:
            print(f"Error updating keyboard: {e}")
        
        return True
    
    return False  # If callback not handled

async def credit_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /creditstats command with enhanced visual presentation
    Display detailed statistics on user's credits
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Show loading message
    loading_message = await update.message.reply_text(
        "⏳ Analizuję dane wykorzystania kredytów..."
    )
    
    try:
        # Pobierz aktualny stan kredytów
        credits = get_user_credits(user_id)
        
        # Stwórz podstawową wiadomość z informacją o kredytach
        message = f"*Analiza kredytów*\n\n"
        message += f"Aktualny stan kredytów: *{credits}*\n\n"
        
        # Spróbuj pobrać bardziej szczegółowe statystyki
        try:
            from database.credits_client import get_user_credit_stats
            stats = get_user_credit_stats(user_id)
            
            if stats:
                # Format daty ostatniego zakupu
                last_purchase = "Brak"
                if stats.get('last_purchase'):
                    if isinstance(stats['last_purchase'], str) and 'T' in stats['last_purchase']:
                        last_purchase = stats['last_purchase'].split('T')[0]
                    else:
                        last_purchase = str(stats['last_purchase'])
                
                message += f"*Statystyki kredytów:*\n"
                message += f"▪️ Łącznie zakupiono: *{stats.get('total_purchased', 0)}* kredytów\n"
                message += f"▪️ Wydano łącznie: *{stats.get('total_spent', 0)}* PLN\n"
                message += f"▪️ Ostatni zakup: *{last_purchase}*\n"
                message += f"▪️ Średnie dzienne zużycie: *{int(stats.get('avg_daily_usage', 0))}* kredytów\n\n"
                
                # Dodaj informację o historii transakcji, jeśli jest dostępna
                if stats.get('usage_history'):
                    message += f"*Historia transakcji (ostatnie 5):*\n"
                    
                    # Pokaż maksymalnie 5 transakcji
                    for i, transaction in enumerate(stats['usage_history'][:5]):
                        date = transaction.get('date', '')
                        if isinstance(date, str) and 'T' in date:
                            date = date.split('T')[0]
                        
                        transaction_type = transaction.get('type', '')
                        amount = transaction.get('amount', 0)
                        description = transaction.get('description', '')
                        
                        if transaction_type in ["add", "purchase", "subscription", "subscription_renewal"]:
                            message += f"🟢 +{amount} kr. ({date})"
                        else:
                            message += f"🔴 -{amount} kr. ({date})"
                            
                        if description:
                            message += f" - {description}"
                            
                        message += "\n"
        except Exception as e:
            print(f"Błąd przy pobieraniu statystyk: {e}")
            message += "*Błąd przy pobieraniu szczegółowych statystyk.*\n\n"
        
        # Dodaj przyciski
        keyboard = [
            [InlineKeyboardButton("💰 Kup więcej kredytów", callback_data="menu_credits_buy")],
            [InlineKeyboardButton("⬅️ Powrót", callback_data="menu_back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Usuń wiadomość ładowania
        await loading_message.delete()
        
        # Wyślij statystyki
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        # Spróbuj wygenerować i wysłać wykresy w osobnych wiadomościach
        try:
            from utils.credit_analytics import generate_credit_usage_chart, generate_usage_breakdown_chart
            
            chart = generate_credit_usage_chart(user_id)
            if chart:
                await update.message.reply_photo(
                    photo=chart,
                    caption="Historia wykorzystania kredytów"
                )
                
            breakdown_chart = generate_usage_breakdown_chart(user_id)
            if breakdown_chart:
                await update.message.reply_photo(
                    photo=breakdown_chart,
                    caption="Rozkład wykorzystania kredytów według kategorii"
                )
        except Exception as e:
            print(f"Błąd przy generowaniu wykresów: {e}")
            # Nie przerywa wykonywania funkcji
            
    except Exception as e:
        print(f"Błąd w credit_stats_command: {e}")
        import traceback
        traceback.print_exc()
        
        # Usuń wiadomość ładowania
        await loading_message.delete()
        
        # Wyślij informację o błędzie
        await update.message.reply_text(
            "Wystąpił błąd podczas generowania statystyk. Spróbuj ponownie później."
        )
        
async def credit_analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Display credit usage analysis
    Usage: /creditstats [days]
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Check if number of days is specified
    days = 30  # Default 30 days
    if context.args and len(context.args) > 0:
        try:
            days = int(context.args[0])
            # Limit range
            if days < 1:
                days = 1
            elif days > 365:
                days = 365
        except ValueError:
            pass
    
    # Inform user that analysis is starting
    status_message = await update.message.reply_text(
        get_text("analyzing_credit_usage", language, default="⏳ Analizuję dane wykorzystania kredytów...")
    )
    
    # Get credit depletion forecast
    depletion_info = predict_credit_depletion(user_id, days)
    
    if not depletion_info:
        await status_message.edit_text(
            get_text("not_enough_credit_history", language, default="Nie masz wystarczającej historii użycia kredytów, aby przeprowadzić analizę. Spróbuj ponownie po wykonaniu kilku operacji."),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Prepare analysis message
    message = f"📊 *{get_text('credit_analytics', language, default='Analiza wykorzystania kredytów')}*\n\n"
    message += f"{get_text('current_balance', language)}: *{depletion_info['current_balance']}* {get_text('credits', language)}\n"
    message += f"{get_text('average_daily_usage', language, default='Średnie dzienne zużycie')}: *{depletion_info['average_daily_usage']}* {get_text('credits', language)}\n"
    
    if depletion_info['days_left']:
        message += f"{get_text('predicted_depletion', language, default='Przewidywane wyczerpanie kredytów')}: {get_text('in_days', language, default='za')} *{depletion_info['days_left']}* {get_text('days', language, default='dni')} "
        message += f"({depletion_info['depletion_date']})\n\n"
    else:
        message += f"{get_text('not_enough_data', language, default='Za mało danych, aby przewidzieć wyczerpanie kredytów.')}.\n\n"
    
    # Get credit usage breakdown
    usage_breakdown = get_credit_usage_breakdown(user_id, days)
    
    if usage_breakdown and sum(usage_breakdown.values()) > 0:
        for category, amount in usage_breakdown.items():
            percentage = amount / sum(usage_breakdown.values()) * 100
            message += f"- {category}: *{amount}* {get_text('credits', language)} ({percentage:.1f}%)\n"
    else:
        message += f"- {get_text('no_data', language, default='Brak dostępnych danych o użyciu.')}\n"
    
    # Send analysis message
    await status_message.edit_text(
        message,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Generate and send usage history chart
    usage_chart = generate_credit_usage_chart(user_id, days)
    
    if usage_chart:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=usage_chart,
            caption=f"📈 {get_text('usage_history_chart', language, default=f'Historia wykorzystania kredytów z ostatnich {days} dni')}"
        )
    
    # Generate and send usage breakdown chart
    breakdown_chart = generate_usage_breakdown_chart(user_id, days)
    
    if breakdown_chart:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=breakdown_chart,
            caption=f"📊 {get_text('usage_breakdown_chart', language, default=f'Rozkład wykorzystania kredytów z ostatnich {days} dni')}"
        )