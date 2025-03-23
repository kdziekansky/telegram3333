"""
Ulepszony moduł do analizy wykorzystania kredytów
"""
import io
import matplotlib.pyplot as plt
import numpy as np
import datetime
import pytz
import logging
from matplotlib.dates import DateFormatter
from database.supabase_client import get_credit_transactions, get_user_credits

# Dodaję loggera dla lepszej diagnostyki
logger = logging.getLogger(__name__)

def generate_credit_usage_chart(user_id, days=30):
    """Generuje wykres użycia kredytów w czasie"""
    try:
        transactions = get_credit_transactions(user_id, days)
        
        if not transactions:
            logger.warning(f"Brak transakcji dla użytkownika {user_id} w okresie {days} dni")
            # Generujemy prosty wykres informacyjny zamiast zwracać None
            plt.text(0.5, 0.5, get_text("no_transaction_data", language), 
            horizontalalignment='center', verticalalignment='center', 
            fontsize=20, color='gray', transform=plt.gca().transAxes)
            
            # Zapisz wykres do bufora
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close()
            return buf
        
        # Przygotuj dane do wykresu
        dates = []
        balances = []
        usage_amounts = []
        purchase_amounts = []
        
        logger.info(f"Znaleziono {len(transactions)} transakcji do analizy")
        
        for trans in transactions:
            try:
                # Konwersja formatu daty
                created_at = trans['created_at']
                if isinstance(created_at, str):
                    dt = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    dt = created_at
                    
                dates.append(dt)
                balances.append(trans['credits_after'])
                
                if trans['transaction_type'] == 'deduct':
                    usage_amounts.append(trans['amount'])
                    purchase_amounts.append(0)
                elif trans['transaction_type'] in ['add', 'purchase', 'subscription', 'subscription_renewal']:
                    usage_amounts.append(0)
                    purchase_amounts.append(trans['amount'])
            except Exception as e:
                logger.error(f"Błąd przy przetwarzaniu transakcji: {e}", exc_info=True)
        
        if not dates:
            logger.warning(f"Nie udało się przetworzyć żadnej transakcji")
            # Generujemy prosty wykres informacyjny
            plt.figure(figsize=(10, 6))
            plt.text(0.5, 0.5, get_text("transaction_processing_error", language), 
                    horizontalalignment='center', verticalalignment='center', 
                    fontsize=20, color='gray', transform=plt.gca().transAxes)
            plt.gca().set_axis_off()
            
            # Zapisz wykres do bufora
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close()
            return buf
        
        plt.figure(figsize=(10, 6))
        
        # Wykres salda
        plt.subplot(2, 1, 1)
        plt.plot(dates, balances, 'b-', label='Saldo kredytów')
        plt.xlabel(get_text("date", language))
        plt.ylabel(get_text("credits", language))
        plt.title(get_text("credit_balance_history", language))
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.gca().xaxis.set_major_formatter(DateFormatter('%d-%m-%Y'))
        plt.gcf().autofmt_xdate()
        plt.legend()
        
        # Wykres użycia/zakupów
        plt.subplot(2, 1, 2)
        
        # Konwertujemy daty na liczby dla łatwiejszego wykreślania słupków
        dates_num = [x.timestamp() for x in dates]
        width = min(7200, (max(dates_num) - min(dates_num)) / len(dates_num) * 0.8) if len(dates_num) > 1 else 7200
        
        # Wykres słupkowy użycia
        usage_bars = plt.bar([d - width/2 for d in dates_num], usage_amounts, width=width, color='r', alpha=0.6, label='Wydane kredyty')
        
        # Wykres słupkowy zakupów
        purchase_bars = plt.bar([d + width/2 for d in dates_num], purchase_amounts, width=width, color='g', alpha=0.6, label='Dodane kredyty')
        
        # Formatowanie osi X
        plt.gca().xaxis.set_major_formatter(DateFormatter('%d-%m-%Y'))
        plt.gcf().autofmt_xdate()
        
        # Etykiety i legenda
        plt.xlabel(get_text("date", language))
        plt.ylabel(get_text("credits", language))
        plt.title(get_text("transaction_details", language))
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        
        # Dopasowanie układu
        plt.tight_layout()
        
        # Zapisz wykres do bufora
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        
        return buf
    
    except Exception as e:
        logger.error(f"Błąd przy generowaniu wykresu: {e}", exc_info=True)
        # Generujemy wykres błędu
        plt.figure(figsize=(10, 6))
        plt.text(0.5, 0.5, get_text("chart_generation_error", language, error=str(e)), 
                horizontalalignment='center', verticalalignment='center', 
                fontsize=12, color='red', transform=plt.gca().transAxes)
        plt.gca().set_axis_off()
        
        # Zapisz wykres do bufora
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        return buf

def get_credit_usage_breakdown(user_id, days=30):
    """Pobiera rozkład zużycia kredytów według rodzaju operacji z dodatkową obsługą błędów"""
    try:
        from database.supabase_client import get_credit_usage_by_type
        breakdown = get_credit_usage_by_type(user_id, days)
        
        # Jeśli brak kategorii, stwórz podstawowy rozkład
        if not breakdown:
            logger.warning(f"Brak danych rozkładu dla użytkownika {user_id} - wykorzystujemy dane transakcji")
            transactions = get_credit_transactions(user_id, days)
            
            # Ręczna kategoryzacja
            breakdown = {"Inne": 0}
            for trans in transactions:
                if trans['transaction_type'] != 'deduct':
                    continue
                    
                description = trans.get('description', '').lower()
                amount = trans.get('amount', 0)
                
                if any(term in description for term in ['wiadomość', 'message', 'chat', 'gpt']):
                    if messages_category not in breakdown:
                        breakdown[messages_category] = 0
                    breakdown[messages_category] += amount
                elif any(term in description for term in ['obraz', 'dall-e', 'image', 'dall']):
                    if images_category not in breakdown:
                        breakdown[images_category] = 0
                    breakdown[images_category] += amount
                elif any(term in description for term in ['dokument', 'document', 'pdf', 'plik']):
                    if documents_category not in breakdown:
                        breakdown[documents_category] = 0
                    breakdown[documents_category] += amount
                elif any(term in description for term in ['zdjęci', 'zdjęc', 'photo', 'foto']):
                    if photos_category not in breakdown:
                        breakdown[photos_category] = 0
                    breakdown[photos_category] += amount
                else:
                    if other_category not in breakdown:
                        breakdown[other_category] = 0
                    breakdown[other_category] += amount
        
        return breakdown
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu rozkładu zużycia: {e}", exc_info=True)
        # Zwracamy prosty słownik w przypadku błędu
        return {"Błąd analizy": 1}

def generate_usage_breakdown_chart(user_id, days=30):
    """Generuje wykres kołowy rozkładu zużycia kredytów z lepszą obsługą błędów"""
    try:
        usage_breakdown = get_credit_usage_breakdown(user_id, days)
        
        if not usage_breakdown:
            logger.warning(f"Brak danych rozkładu dla użytkownika {user_id}")
            # Generujemy prosty wykres informacyjny zamiast zwracać None
            plt.figure(figsize=(8, 6))
            plt.text(0.5, 0.5, get_text("no_analysis_data", language), 
                    horizontalalignment='center', verticalalignment='center', 
                    fontsize=20, color='gray', transform=plt.gca().transAxes)

            plt.gca().set_axis_off()
            
            # Zapisz wykres do bufora
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close()
            return buf
        
        plt.figure(figsize=(8, 6))
        
        labels = list(usage_breakdown.keys())
        sizes = list(usage_breakdown.values())
        
        # Ustaw kolory dla wykresów
        colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#c2c2f0', '#ffb366', '#ff6666']
        
        if sum(sizes) > 0:  # Sprawdź, czy są dane do wykreślenia
            plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, shadow=True)
            plt.axis('equal')
            plt.title(get_text("credit_usage_breakdown_days", language, days=days))
        else:
            plt.text(0.5, 0.5, get_text("no_credit_usage_transactions", language), 
                    horizontalalignment='center', verticalalignment='center', 
                    fontsize=16, color='gray', transform=plt.gca().transAxes)
            plt.gca().set_axis_off()
        
        # Zapisz wykres do bufora
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        
        return buf
    
    except Exception as e:
        logger.error(f"Błąd przy generowaniu wykresu rozkładu: {e}", exc_info=True)
        # Generujemy wykres błędu
        plt.figure(figsize=(8, 6))
        plt.text(0.5, 0.5, get_text("chart_generation_error", language, error=str(e)), 
                horizontalalignment='center', verticalalignment='center', 
                fontsize=12, color='red', transform=plt.gca().transAxes)
        plt.gca().set_axis_off()
        
        # Zapisz wykres do bufora
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        return buf

def predict_credit_depletion(user_id, days=30):
    """Przewiduje, kiedy skończą się kredyty użytkownika z ulepszoną logiką"""
    try:
        transactions = get_credit_transactions(user_id, days)
        current_balance = get_user_credits(user_id)
        
        # Poprawiono logikę sprawdzania danych
        if not transactions:
            logger.warning(f"Brak transakcji dla użytkownika {user_id}")
            return {
                "days_left": None, 
                "average_daily_usage": 0, 
                "current_balance": current_balance,
                "depletion_date": None
            }
        
        # Wyfiltruj transakcje typu 'deduct'
        deduct_transactions = [t for t in transactions if t.get('transaction_type') == 'deduct']
        
        # Jeśli brak transakcji wydatkowych, zwróć None dla days_left
        if not deduct_transactions:
            logger.info(f"Brak transakcji wydatkowych dla użytkownika {user_id}")
            return {
                "days_left": None, 
                "average_daily_usage": 0, 
                "current_balance": current_balance,
                "depletion_date": None
            }
        
        # Oblicz całkowite zużycie w okresie
        total_usage = sum(trans.get('amount', 0) for trans in deduct_transactions)
        
        # Średnie dzienne zużycie nie może być 0
        average_daily_usage = max(total_usage / days, 0.01)
        
        # Oblicz dni do wyczerpania
        days_left = int(current_balance / average_daily_usage) if average_daily_usage > 0 else None
        
        # Określ datę wyczerpania
        depletion_date = None
        if days_left is not None:
            depletion_date = (datetime.datetime.now() + datetime.timedelta(days=days_left)).strftime("%d.%m.%Y")
        
        # Zwróć kompletne informacje
        return {
            "days_left": days_left,
            "depletion_date": depletion_date,
            "average_daily_usage": round(average_daily_usage, 2),
            "current_balance": current_balance
        }
        
    except Exception as e:
        logger.error(f"Błąd w predict_credit_depletion: {e}", exc_info=True)
        # Zwróć podstawowe dane nawet w przypadku błędu
        return {
            "days_left": None,
            "depletion_date": None,
            "average_daily_usage": 0,
            "current_balance": get_user_credits(user_id)
        }