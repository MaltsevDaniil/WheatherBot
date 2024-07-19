from zoneinfo import ZoneInfo

import telebot
import urllib.request
import urllib.parse
import translators as ts
import datetime
import json
import pytz
import mysql.connector as con
from telebot import types

connection = con.connect(
    host='localhost',
    user='root',
    password='root',
    database='botusers',
    port=8889
)

bot = telebot.TeleBot('***');

def get_json(city):
    urlcity = urllib.parse.quote(city)
    result_bytes = urllib.request.urlopen(
        f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/" + urlcity + f"/{datetime.datetime.now().strftime("%Y-%m-%d")}/?unitGroup=metric&include=hours%2Cdays%2Ccurrent&key=FG4ZT3HAGZKAHHK79MHMAZCLZ&contentType=json")
    return json.load(result_bytes)
def get_description_of_day(message, json_data):
    description = ts.translate_text(json_data['days'][0]['description'], 'yandex', to_language='ru')
    bot.send_message(message.from_user.id, description)

def get_max_temp_of_day(message, city, jsonData):
    bot.send_message(message.from_user.id,
                     f"Максимальная температура в городе {city} - {jsonData['days'][0]['tempmax']}°C")

def get_min_temp_of_day(message, city, jsonData):
    bot.send_message(message.from_user.id,
                     f"Минимальная температура в городе {city} - {jsonData['days'][0]['tempmin']}°C")

def get_temp(message, jsonData):
    bot.send_message(message.from_user.id,
                     f"Температура сейчас - {jsonData['days'][0]['hours'][int(datetime.datetime.now().astimezone(pytz.timezone(jsonData['timezone'])).strftime("%H"))]['temp']}°C ")
def get_wind_speed(message, jsonData):
    bot.send_message(message.from_user.id,
                     f'Скорость ветра до {int(jsonData['days'][0]['hours'][int(datetime.datetime.now().astimezone(pytz.timezone(jsonData['timezone'])).strftime("%H"))]['windspeed'])} километров в час')

@bot.message_handler(commands=['help'])
def help_info(message):
    bot.reply_to(message,
                 "Привет!\n В этом боте доступно несколько команд:\n /help - дает информацию о доступных командах \n /start - начинает работу программы \n /savename - позволяет выбрать город, данные о погоде которого будут выводиться при нажатии кнопки 'Погода в моем городе'")


@bot.message_handler(commands=['start'])
def send_welcome(message):
    update_or_create_user_preferences(message.from_user.id)
    button(message)


def button(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Погода в моем городе")
    markup.add(btn1)
    bot.send_message(message.chat.id, text="Привет! Напиши мне свой город, и я напишу тебе погоду в нем!",
                     reply_markup=markup)


@bot.message_handler(commands=['savename'])
def save_city_name(message):
    bot.reply_to(message, "Напиши название города, который ты хочешь видеть при нажатии кнопки 'Погода в моем городе'")
    bot.register_next_step_handler(message, add_saved_city_to_db)


@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    if message.text == 'Погода в моем городе':
        weather_in_my_city(message)
    else:
        process_user_city_input(message.text, message)



def update_or_create_user_preferences(user_id):
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    if not(result):
        cursor.execute(
            "INSERT INTO users (user_id, remember_city) VALUES (%s, NULL)",
            (user_id,))

    connection.commit()
    cursor.close()


def add_saved_city_to_db(message):
    process_user_city_input(message, message)


def process_user_city_input(city, message):
    # Обработка введенного пользователем города и отправка информации о погоде
    try:
        json_data = get_json(city)
        send_weather_info(message, city, json_data)
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        error_info = e.read().decode()
        print('Error: ', e, error_info)
        bot.send_message(message.from_user.id, 'Такого города не существует, попробуйте написать его по-другому')


def send_weather_info(message, city, json_data):
    get_description_of_day(message, json_data)
    get_max_temp_of_day(message, city, json_data)
    get_min_temp_of_day(message, city, json_data)
    get_temp(message, json_data)
    get_wind_speed(message, json_data)


def add_saved_city_to_db(message):
    cursor = connection.cursor()
    request_to_insert_data = '''
    UPDATE users SET remember_city = %s WHERE user_id = %s
    '''
    values = (message.text, message.from_user.id)
    cursor.execute(request_to_insert_data, values)
    connection.commit()
    cursor.close()




def weather_in_my_city(message):
    cursor = connection.cursor()
    cursor.execute("SELECT remember_city FROM users WHERE user_id = %s", (message.from_user.id,))
    result = cursor.fetchone()
    cursor.close()

    if result and result[0]:
        city = result[0]
        send_weather_info(message, city, get_json(city))
    else:
        bot.send_message(message.chat.id, "Город не был выбран. Используйте команду /savename, чтобы выбрать город.")


bot.polling(none_stop=True, interval=0)
