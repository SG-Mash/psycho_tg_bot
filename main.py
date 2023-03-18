from telebot import TeleBot, types
from os import getenv
import datetime as dt
import sqlite3 as sl
import json
from dotenv import load_dotenv

load_dotenv()

bot_token = getenv('TOKEN')
bot = TeleBot(bot_token)

conn = sl.connect('database.db', check_same_thread=False)
cursor = conn.cursor()

result = 0
conclusion = ''


def db_add_user(tg_user_id, first_name, last_name, tg_username):
    cursor.execute(
        'INSERT INTO Users (tg_user_id, first_name, last_name, tg_username) VALUES (?, ?, ?, ?)',
        (tg_user_id, first_name, last_name, tg_username)
    )
    conn.commit()


def user_exists_in_db(user_id):
    user_info = cursor.execute(
        'SELECT * FROM Users WHERE tg_user_id=?', (user_id,)
    ).fetchone()
    return user_info


def add_survey_result_in_db(user_id, survey_name, survey_result, survey_date):
    cursor.execute(
        'INSERT INTO surveys (user_id, survey_name, survey_result, survey_date) VALUES(?, ?, ?, ?)',
        (user_id, survey_name, survey_result, survey_date)
    )
    conn.commit()


def get_passed_survey_info(user_id):
    data = cursor.execute(
        'SELECT survey_date, survey_name, survey_result FROM surveys WHERE user_id=?', (user_id,)
    ).fetchall()
    return data


def get_data_from_txt_file(file_name):
    with open(file_name, encoding='utf-8') as file:
        text = file.read()
    return text


def break_test(message):
    global result
    result = 0
    bot.send_message(message.chat.id, 'Тест прерван', reply_markup=types.ReplyKeyboardRemove())


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, f'👋 Привет! {message.from_user.username}')
    bot.send_message(
        message.chat.id,
        'Здесь собраны тесты, которые помогут тебе определить твое психологическое состояние'
    )
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    username = message.from_user.username
    if not user_exists_in_db(user_id):
        db_add_user(user_id, first_name, last_name, username)


@bot.message_handler(commands=['my_tests'])
def my_passed_tests(message):
    surveys = get_passed_survey_info(message.from_user.id)
    if len(surveys) != 0:
        bot.send_message(message.chat.id, 'Ваши пройденные тесты:')
        for survey in surveys:
            text = f'Дата прохождения: {survey[0]}\nТест: {survey[1]}\nРезультат: {str(survey[2])}'
            bot.send_message(message.chat.id, text)
    else:
        bot.send_message(message.chat.id, 'Вы еще не проходили тесты')


@bot.message_handler(commands=['description'])
def description(message):
    bot.send_message(message.chat.id, get_data_from_txt_file('about/about_bot.txt'))


@bot.message_handler(commands=['author'])
def about_author(message):
    bot.send_message(message.chat.id, get_data_from_txt_file('about/about_author.txt'))


@bot.message_handler(commands=['stat'])
def bot_data(message):
    if message.from_user.id == 21662680 or message.from_user.id == 1536319383:
        bot_users_qty = cursor.execute(
            'SELECT COUNT(*) FROM Users'
        ).fetchone()
        text = f'Кол-во человек, запускавших бот: {str(bot_users_qty[0])}'
        bot.send_message(message.chat.id, text)
        with open('list_of_tests.json', encoding='utf-8') as json_file:
            surveys = json.load(json_file)
        for survey in surveys.keys():
            survey_count = cursor.execute(
                'SELECT COUNT(survey_name) FROM Surveys WHERE survey_name=?', (survey,)
            ).fetchone()
            text = f'Кол-во прохождений теста "{survey}": {str(survey_count[0])}'
            bot.send_message(message.chat.id, text)
    else:
        my_passed_tests(message)


@bot.message_handler(commands=['tests'])
def test_choice(message):
    global result, conclusion
    result = 0
    conclusion = ''
    markup = types.InlineKeyboardMarkup()
    with open('list_of_tests.json', encoding='utf-8') as json_file:
        data = json.load(json_file)
    for key, value in data.items():
        markup.add(types.InlineKeyboardButton(key, callback_data=value))
    bot.send_message(message.chat.id, 'Выберете тест:', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def test_switcher(call):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('🤓 Начать'))
    if call.data == 'Beck test':
        bot.send_message(
            call.message.chat.id,
            get_data_from_txt_file('surveys/beck_test_description.txt'),
            reply_markup=markup,
            parse_mode='html'
        )
        bot.register_next_step_handler(
            call.message,
            test_run,
            '1',
            'surveys/beck_test.json',
            'surveys/beck_test_recommendations.txt'
        )
    elif call.data == 'Self-esteem':
        bot.send_message(
            call.message.chat.id,
            get_data_from_txt_file('surveys/kovalev_test_description.txt'),
            reply_markup=markup,
            parse_mode='html'
        )
        bot.register_next_step_handler(
            call.message,
            test_run,
            '1',
            'surveys/kovalev_test.json',
            'surveys/kovalev_test_recommendations.txt'
        )


def test_run(message, question_number, file_json, file_txt):
    global result, conclusion
    with open(file_json, encoding='utf-8') as json_file:
        data = json.load(json_file)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for answer in data['answers']:
        markup.add(types.KeyboardButton(answer))
    if message.text == '🤓 Начать' or message.text in data['answers']:
        if question_number in data['questions'].keys():
            bot.send_message(message.chat.id, f'Вопрос {question_number}')
            bot.send_message(message.chat.id, data['questions'][question_number], reply_markup=markup)
            bot.register_next_step_handler(
                message,
                result_calculation,
                question_number,
                data['answers'],
                data['answer_points'],
                file_json,
                file_txt
            )
        else:
            for key, points in data['result_points'].items():
                if points[0] <= result <= points[1]:
                    conclusion = key
                    break
            text = f'Ваш результат: <b>{result}</b>. {data["conclusion"][conclusion]}\n{data["recommendation"]}'
            bot.send_message(message.chat.id, text, reply_markup=types.ReplyKeyboardRemove(), parse_mode='html')
            bot.send_message(message.chat.id, get_data_from_txt_file(file_txt), parse_mode='html')
            user_id = message.from_user.id
            survey_name = data['survey_name']
            survey_result = result
            survey_date = dt.datetime.now().strftime('%H:%M:%S %d-%m-%Y')
            add_survey_result_in_db(user_id, survey_name, survey_result, survey_date)
    else:
        break_test(message)


def result_calculation(message, question_number, answers, points, file_json, file_txt):
    global result
    if message.text in answers:
        result += points[answers.index(message.text)]
        test_run(message, str(int(question_number) + 1), file_json, file_txt)
    else:
        break_test(message)


def main():
    bot.polling(none_stop=True)


if __name__ == '__main__':
    main()
