from telegram.ext import *
import chatterbot
import logging
import re
import json
import urllib
import datetime

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

chat_bot = None

def start(bot, update):
    update.message.reply_text('Bot is now in English. A multi-language too')

def hello(bot, update):
    update.message.reply_text('Hello {}'.format(update.message.from_user.first_name))

def process_text(text): # todo rename and debidlo
    aud_msg = parse_auditory_number(text)

    url =  urllib.request.urlopen("http://cist.nure.ua/ias/app/tt/").read()
    cist_schedule = json.loads(url)

    return aud_msg

def get_schedule(group, date = None):
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
    if g_entry['group_name'] == search_group:
       group_id = g_entry['group_id']
     
  assert(group_id != None)
  
  group_url = cist_api_root + "/get_schedule?group_id=" + str(group_id)
  group_json = urllib.request.urlopen(group_url).read().decode('UTF-8')
  group_sched = json.loads(group_json)

  try:
    schedule_date = datetime.datetime.strptime(date, "%d.%m.%Y") if date != None else datetime.datetime.today()
  except ValueError:
    return "FCUKYOU!!1 khm.. Try to input a valid dd.mm.YYYY date representation"

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
  
    schedule_date_ddmmyear = str(schedule_date.day) + "." + str(schedule_date.month) + "." + str(schedule_date.year) # date in dd.mm.year foramt as in api

    for lesson_date in dates:
      if (lesson_date == schedule_date_ddmmyear):
        today_lessons.append(l)
  
  schedule_info = ""
  for lesson in today_lessons:
    lesson_info = lesson['subject'] + " [" + lesson['time_start'] + " - " + lesson['time_end'] + "] " + " aud: " + str(lesson['auditories'][0]['auditory_name']) + "\r\n"
    schedule_info += lesson_info

  return schedule_info

def parse_auditory_number(text):
    numbers = re.findall(r'\b\d+[а-я]?\b', text)
    
    if not numbers:
      return ""

    for number in numbers:
        answer = ""
        if (not number[len(number) - 1].isdigit()):
            if (number[len(number) - 1] == 'и'):
              answer += "Корпус И "
            elif (number[len(number) - 1] == 'з'):
              answer += "Корпус З "
            else:
              answer += "Главный корпус "  
        else:
            answer += "Главный корпус "
        
        answer += "Этаж " + number[0]
        
        return answer

def auditory(bot, update):
    update.message.reply_text("DSOKDOSK")

def message_handler(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text=chat_bot.get_response(update.message.text).text)
    bot.sendMessage(chat_id=update.message.chat_id, text=process_text(update.message.text))


get_schedule("ПЗСм-16-1")

chat_bot = chatterbot.ChatBot("NUREbot", 
      storage_adapter = "chatterbot.adapters.storage.JsonFileStorageAdapter",
      logic_adapters = ["chatterbot.adapters.logic.MathematicalEvaluation",
        "chatterbot.adapters.logic.TimeLogicAdapter",
        "chatterbot.adapters.logic.ClosestMatchAdapter",])
chat_bot.set_trainer(chatterbot.trainers.ChatterBotCorpusTrainer)
chat_bot.train("chatterbot.corpus.english")

updater = Updater('259933822:AAGoMk2Fb2YwBP6bOMl69a4E7DDmXBrxtz4')

updater.dispatcher.add_handler(MessageHandler([Filters.text], message_handler))
updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('hello', hello))
updater.dispatcher.add_handler(CommandHandler('auditory', auditory))

updater.start_polling()
updater.idle()