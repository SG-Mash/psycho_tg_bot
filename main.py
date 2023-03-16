import telebot
from telebot import types
import os
import json
from dotenv import load_dotenv

load_dotenv()

bot_token = os.getenv('TOKEN')
bot = telebot.TeleBot(bot_token)

result = 0
conclusion = ''


def get_data_from_txt_file(file_name):
    with open(file_name, encoding='utf-8') as file:
        text = file.read()
    return text


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, f'👋 Привет! {message.from_user.username}')
    bot.send_message(
        message.chat.id,
        'Здесь собраны тесты, которые помогут тебе определить твое психологическое состояние'
    )


@bot.message_handler(commands=['description'])
def description(message):
    bot.send_message(message.chat.id, get_data_from_txt_file('about_bot.txt'))


@bot.message_handler(commands=['author'])
def about_author(message):
    bot.send_message(message.chat.id, get_data_from_txt_file('about_author.txt'))


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
    bot.send_message(message.chat.id, 'Выберете тест', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def test_switcher(call):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Начать'))
    if call.data == 'Beck test':
        bot.send_message(
            call.message.chat.id,
            get_data_from_txt_file('beck_test_description.txt'),
            reply_markup=markup,
            parse_mode='html'
        )
        bot.register_next_step_handler(call.message, test_run, '1', 'beck_test.json')
    elif call.data == 'one more test':
        bot.send_message(call.message.chat.id, 'One more test')
    elif call.data == 'New test':
        bot.send_message(call.message.chat.id, 'New test')


def test_run(message, question_number, file_name):
    global result, conclusion
    with open(file_name, encoding='utf-8') as json_file:
        data = json.load(json_file)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for answer in data['answers']:
        markup.add(types.KeyboardButton(answer))
    if question_number in data['questions'].keys():
        bot.send_message(message.chat.id, f'Вопрос {question_number}')
        bot.send_message(message.chat.id, data['questions'][question_number], reply_markup=markup)
        bot.register_next_step_handler(
            message,
            result_calculation,
            question_number,
            data['answers'],
            data['answer_points'],
            file_name
        )
    else:
        for key, points in data['result_points'].items():
            if points[0] <= result <= points[1]:
                conclusion = key
                break
        text = f'Ваш результат: <b>{result}</b>. {data["conclusion"][conclusion]}\n{data["recommendation"]}'
        bot.send_message(message.chat.id, text, reply_markup=types.ReplyKeyboardRemove(), parse_mode='html')


def result_calculation(message, question_number, answers, points, file_name):
    global result
    result += points[answers.index(message.text)]
    test_run(message, str(int(question_number) + 1), file_name)


def main():
    bot.polling(none_stop=True)


if __name__ == '__main__':
    main()
