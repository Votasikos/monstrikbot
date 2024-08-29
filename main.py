import requests
from bs4 import BeautifulSoup
import json
import time
import tweepy
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Načtení proměnných prostředí ze souboru .env
load_dotenv()

# Získání Twitter API přihlašovacích údajů z proměnných prostředí
consumer_key = os.getenv('TWITTER_CONSUMER_KEY')
consumer_secret = os.getenv('TWITTER_CONSUMER_SECRET')
access_token = os.getenv('TWITTER_ACCESS_TOKEN')
access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')

# Autentizace na Twitteru pomocí API v2
client = tweepy.Client(
    bearer_token=None,  # Volitelné, pokud používáte pouze OAuth 1.0a
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    access_token=access_token,
    access_token_secret=access_token_secret
)

# URL sledované stránky
url = 'https://www.kupi.cz/sleva/energeticky-napoj-monster-energy'

# Funkce pro kontrolu slevy na stránce
def check_sale():
    try:
        response = requests.get(url)
        response.raise_for_status()  # Ověří, že odpověď byla úspěšná
        soup = BeautifulSoup(response.content, 'html.parser')

        # Vyhledání tagu script obsahujícího JSON-LD data
        script_tag = soup.find('script', type='application/ld+json')
        if script_tag:
            json_data = json.loads(script_tag.string)
            print(json.dumps(json_data, indent=4))  # Vytiskne JSON data pro kontrolu

            # Úprava na základě skutečné struktury JSON dat
            offers = json_data.get('offers', [])
            if not isinstance(offers, list):
                offers = offers.get('offers', [])  # Úprava podle skutečné struktury

            sale_info = []
            for offer in offers:
                if isinstance(offer, dict):
                    price = offer.get('price', float('inf'))
                    offered_by = offer.get('offeredBy', 'Neznámý obchod')
                    sale_info.append({
                        'price': price,
                        'offeredBy': offered_by
                    })
                else:
                    print(f"Nečekaný formát nabídky: {offer}")

            return sale_info

    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"Chyba při stahování nebo zpracování stránky: {e}")

    return None

# Funkce pro odeslání tweetu
def post_tweet(tweet_text):
    try:
        # Odeslat tweet
        response = client.create_tweet(text=tweet_text)
        print(f"Tweet odeslán s ID {response.data['id']}")
    except tweepy.TweepyException as e:
        print(f"Chyba při odesílání tweetu: {e.response.json()['errors'][0]['detail']}")

# Funkce pro formátování informací o slevách pro tweetování
def format_sale_info(sale_info):
    tweet_text = '🎉 Monster Energy Drink je v akci!\n――――――――――――――――――\n'
    if sale_info:
        for info in sale_info:
            tweet_text += f'» {info["offeredBy"]}: Cena: {info["price"]} Kč\n'
    else:
        tweet_text += 'Momentálně žádné nabídky. 😭'
    
    return tweet_text

# Funkce pro odeslání tweetu v 5 ráno
def schedule_tweet():
    current_time = datetime.now()
    target_time = current_time.replace(hour=23, minute=0, second=0, microsecond=0)

    # Pokud je čas už po 5 ráno, naplánujeme tweet na další den
    if current_time > target_time:
        target_time += timedelta(days=1)

    # Vypočítat dobu do příštího tweetu
    time_to_wait = (target_time - current_time).total_seconds()

    return target_time, time_to_wait

# Funkce pro logování stavu
def log_status(target_time):
    current_time = datetime.now()
    time_to_wait = (target_time - current_time).total_seconds()
    hours, remainder = divmod(time_to_wait, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    log_message = (
        f"Stále běží: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Čas do dalšího tweetu: {int(hours)} hodin {int(minutes)} minut {int(seconds)} sekund"
    )
    print(log_message)
    
    with open('tweet_log.txt', 'a') as log_file:
        log_file.write(log_message + '\n')

# Hlavní cyklus pro pravidelnou kontrolu
def main():
    while True:
        target_time, time_to_wait = schedule_tweet()
        
        while True:
            log_status(target_time)
            time.sleep(3600)  # Logovat každou hodinu
            
            # Zkontrolovat čas znovu
            current_time = datetime.now()
            if current_time >= target_time:
                sale_info = check_sale()
                tweet_text = format_sale_info(sale_info)
                post_tweet(tweet_text)
                
                # Po odeslání tweetu naplánovat další tweet na další den
                target_time, time_to_wait = schedule_tweet()
                break

if __name__ == '__main__':
    main()
