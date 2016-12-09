#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import *
from telegram import *
import chatterbot
import logging
import re
import json
import urllib
import datetime

from Crypto.Cipher import AES
import base64

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# store encrypted keys to avoid simple github search for tokens
crypter = AES.new('76B305DACD6BE18BBF07F1DFB0C57E65', AES.MODE_ECB)
TELEGRAM_ACCESS_TOKEN_ENCRYPTED = b'\x1ed4\x85\xfcf\x03\xfc=\xd6\xcc\xdb\x06h\xe6\xed\x98=+4d\x9a\xb7\x87\xd2\xcb\xc4\xe7\xb4\xe6^\x98)\x0b1\xce\xb4\x9ai\x96r*\x10\xfe\xafe\x96\x1d'
MONGO_URI_STRING_ENCRYPTED = b'\xcb\x8d\x90\xb9\x1c\x81\x82\x18\xd5\xfaf@\xea"ePv\x07\xed\xc2\xc9\xcd7\xf8\x8b\x02\x9a\xed\xce\xc9\xc1C\x1fA\x19\x1d\xe6Q9\t9\xec\xb7\x17]}\xca^\x18lzC\xa3\xd0\xee\x1f\xe8o5#\xe9\xea\xaaa'
TELEGRAM_ACCESS_TOKEN = str(crypter.decrypt(TELEGRAM_ACCESS_TOKEN_ENCRYPTED).strip())[2:-1] # crop unnecessary braces and stuff 
MONGO_URI_STRING = str(crypter.decrypt(MONGO_URI_STRING_ENCRYPTED).strip())[2:-1] # crop unnecessary braces and stuff 

chat_bot = None
is_learning_enabled = False # todo move learning to separate instance

def process_text(text: str) -> str:
  """
  Proxy regular text to the current bot model
  Parametrs:
    text - string, user input

  Returns:
    string, bot calculated response
  """
  bot_response = chat_bot.get_response(text)
    
  return bot_response

def get_schedule(group: str, date: str = None) -> str:
  """
  Get schedule for a group by its name for one full day.
  Schedule source - NURE official api (http://cist.nure.ua/ias/app/tt)
  Date is optional. No date specified = today

  Parametrs:
    group - string, group title
    date  - string, optional. Date format should be zero-padded and dot delimited "dd.mm.YYYY" ("01.12.2016")

  Returns:
    string, formatted schedule info
  """
  # caption independent search
  group = group.lower()

  # api spec 
  # https://docs.google.com/document/d/1BPZkBa5Y_gcGj25Q3eVm7Ftxh0_NG4a1DYhKR-jjfNQ/edit
  cist_api_root = "http://cist.nure.ua/ias/app/tt"
  faculties_url =  urllib.request.urlopen(cist_api_root + "/get_faculties").read()
  faculties = json.loads(faculties_url.decode('UTF-8'))
  
  # find all groups to search schedule by a short groupname
  all_groups = []
  for f_entry in faculties['faculties']:
    faculty_id = f_entry['faculty_id']
    groups_url = cist_api_root + "/get_groups?faculty_id=" + str(faculty_id)
    groups_json = urllib.request.urlopen(groups_url).read().decode('UTF-8')
    groups = json.loads(groups_json)
    all_groups = all_groups + groups['groups']
  
  assert(all_groups != [])

  group_id = None
  search_group = group
  for g_entry in all_groups:
    if g_entry['group_name'].lower() == search_group:
       group_id = g_entry['group_id']
       break
     
  if group_id == None:
    return "Group not found"
  
  group_url = cist_api_root + "/get_schedule?group_id=" + str(group_id)
  group_json = urllib.request.urlopen(group_url).read().decode('UTF-8')
  group_sched = json.loads(group_json)

  try:
    schedule_date = datetime.datetime.strptime(date, "%d.%m.%Y") if date != None else datetime.datetime.today()
  except ValueError:
    return "Input a valid dd.mm.YYYY date representation as the second argument"

  # double conversion to ensure valid string date format
  schedule_date_ddmmyear = schedule_date.strftime("%d.%m.%Y")

  weekday = schedule_date.weekday() # Returns the day of the week as an integer, where Monday is 0 and Sunday is 6.
  day_sched = group_sched['days'][weekday]
  lessons = day_sched['lessons']
  today_lessons = []
  for l in lessons:
    dates = None
    if 'date_start' in l:
      dates = [l['date_start']]
    elif 'dates' in l:
      dates = l['dates']
    
    assert(dates != None)
  
    for lesson_date in dates:
      if (lesson_date == schedule_date_ddmmyear):
        today_lessons.append(l)
  
  if not today_lessons:
    return "Нет занятий или сервер недоступен"

  schedule_info = ""
  for lesson in today_lessons:
    subject = lesson['subject']
    teacher = lesson['teachers'][0]['teacher_name'] if lesson['teachers'] else "" # get first and only teacher if specified
    time = "[" + lesson['time_start'] + " - " + lesson['time_end'] + "]"
    auditorium = "/aud " + str(lesson['auditories'][0]['auditory_name'])
    lesson_info = subject + "\r\n" + teacher + "\r\n" + time + "\r\n" + auditorium + "\r\n" + "\r\n"
    schedule_info += lesson_info

  return schedule_info

# TODO get more info about placings
def parse_auditory_number(text):
  """
  Get directions to auditorium including building, floor.

  Parametrs:
    text - string, number as represented in schedule ("42з")

  Returns:
    string, formatted directions info
  """

  numbers = re.findall(r'\b\d+[а-я]?\b', text)
  
  if not numbers:
    return "Неправильный формат аудитории"

  if text == "спорт":
    return "Спортзал находится на четвертом этаже. Пройти туда можно зайдя в главный вход университета, повернув налево, пройдя по коридору, затем повернув направо, продя по коридору и поднявшись по лестнице, которая там находится"
  
  # should contain only one number in the list for my purpose
  assert(len(numbers) == 1)

  info = ""
  for number in numbers:
    answer = ""
    path_info = ""
    if (not number[len(number) - 1].isdigit()):
        if (number[len(number) - 1] == 'и'):
          answer += "Корпус <И> "
        elif (number[len(number) - 1] == 'з'):
          answer += "Корпус <З> "
          path_info += "Проще пройти через главный корпус. Главный вход, второй этаж и сразу налево, если идти по главной лестнице. Затем по крытому переходу в корпус З"
    else:
        answer += "Главный корпус "
        aud = int(number[1:len(number)])
        if aud < 50:
          path_info += "Слева, если идти по главной лестнице"
        else:
          path_info += "Справа, если идти по главной лестнице"

    answer += "Этаж " + number[0] + " \r\n" + path_info
    
    info += answer
    
  return info

# args should contain the actual number
def auditory(bot, update, args):
  """
  Bot proxy method to send auditorium directions in text fromat to user.

  Parametrs:
  bot    - telegram.ext bot object
  update - telegram.ext update object
  args   - list of string parametres passed through command (/aud 42з -> args = ['42з']
  """
  if len(args) != 1:
    update.message.reply_text("Example usage: /aud 42з")
  else:
    path_message = parse_auditory_number(args[0])
    update.message.reply_text("Она находится : " + path_message)

def schedule(bot, update, args):
  """
  Bot proxy method to send schedule info in text fromat to user.

  Parametrs:
  bot    - telegram.ext bot object
  update - telegram.ext update object
  args   - list of string parametres passed through command (/schedule ПЗСм-16-1 26.12.2016 -> args = ['42з', '26.12.2016']
  """
  argc = len(args)
  schedule_message = None

  # bad construction, redo in a conviniet way
  if argc == 0:
    update.message.reply_text("Example usage: /sched ПЗСм-16-1 [28.12.2016]" + "\n [date] is optional. Not specified = today")
    return
  elif argc == 1:
    schedule_message = get_schedule(args[0])
  elif argc == 2:
    schedule_message = get_schedule(args[0], args[1])

  update.message.reply_text(schedule_message)

# TODO maybe get rid of double layer of proxy from chatterbot
def message_handler(bot, update):
  """
  Bot proxy method to process non-command user text.
  Uses process_text method

  Parametrs:
  bot    - telegram.ext bot object
  update - telegram.ext update object
  """
  resp = process_text(update.message.text).text
  bot.sendMessage(
    chat_id=update.message.chat_id, 
    text=resp
  )

def help(bot, update):
  """
  Conversation engager. Acts as basic help about commands and bot capabilities

  Parametrs:
  bot    - telegram.ext bot object
  update - telegram.ext update object
  """
  reply_keyboard = [['O K']]

  update.message.reply_text(
    "Я нурешный бот. Могу рассказать про расположение аудиторий, столовых, туалетов. "
    "Расписание на один день на группу. Можем просто поговорить на какие-то темы. \n"
    "Сейчас я понимаю русский, english и немного других языков. \n"
    "Мои команды с примером использования: /aud 322и , /sched ПЗСм-16-1 07.12.2016 , /sched ПЗСм-16-1 \n"
    "Все ли понятно?",
    reply_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
  )

#
# Create and init bot
#

chat_bot = chatterbot.ChatBot("NUREbot", 
      storage_adapter = "chatterbot.storage.MongoDatabaseAdapter",
      database = "nure-bot",
      database_uri = MONGO_URI_STRING,
      logic_adapters = [
        {
            'import_path': 'chatterbot.logic.LowConfidenceAdapter',
            'threshold': 0.45,
            'default_response': 'Я не понимаю, надо перефразировать.'
        },
        {
            'import_path': 'chatterbot.logic.BestMatch',
            'statement_comparison_function': 'chatterbot.comparisons.synset_distance',
            'response_selection_method': 'chatterbot.response_selection.get_random_response'
        },
        {
            'import_path': 'chatterbot.logic.MathematicalEvaluation'
        },
        {
            'import_path': 'chatterbot.logic.TimeLogicAdapter'
        }
      ]
)

if is_learning_enabled:
  chat_bot.set_trainer(chatterbot.trainers.ChatterBotCorpusTrainer)
  chat_bot.train("chatterbot.corpus.english")
  chat_bot.train("chatterbot.corpus.russian")
  chat_bot.train("chatterbot.corpus.chinese")
  chat_bot.train("chatterbot.corpus.french")
  chat_bot.train("chatterbot.corpus.german")
  chat_bot.train("chatterbot.corpus.hindi")
  chat_bot.train("chatterbot.corpus.indonesia")
  chat_bot.train("chatterbot.corpus.italian")
  chat_bot.train("chatterbot.corpus.marathi")
  chat_bot.train("chatterbot.corpus.portuguese")
  chat_bot.train("chatterbot.corpus.spanish")
  chat_bot.train("chatterbot.corpus.telugu")
  
  chat_bot.train("corpus.nure")

updater = Updater(TELEGRAM_ACCESS_TOKEN)

updater.dispatcher.add_handler(MessageHandler(Filters.text, message_handler))
updater.dispatcher.add_handler(CommandHandler(command = 'aud', callback = auditory, pass_args = True))
updater.dispatcher.add_handler(CommandHandler(command = 'schedule', callback = schedule, pass_args = True))
updater.dispatcher.add_handler(CommandHandler(command = 'start', callback = help))
updater.dispatcher.add_handler(CommandHandler(command = 'help', callback = help))

updater.start_polling()
updater.idle()