from telegram.ext import *
import chatterbot
import logging
import re
import json
import urllib
import datetime

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

chat_bot = None

def process_text(text): # todo rename and debidlo
    bot_response = chat_bot.generate_response(text)
      
    return bot_response

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

# args should contain the actual number
def auditory(bot, update, args):
    if len(args) != 1:
      update.message.reply_text("Example usage: /aud 42з")
    else:
      path_message = parse_auditory_number(args[0])
      update.message.reply_text("Она находится : " + path_message)

def message_handler(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text=chat_bot.get_response(update.message.text).text)
    bot.sendMessage(chat_id=update.message.chat_id, text=process_text(update.message.text))


#get_schedule("ПЗСм-16-1")

# look for data
# http://www.nltk.org/data.html
# delete if it sucks
# C:\Users\dshpet\AppData\Roaming\nltk_data
import nltk
# read
# http://www.nltk.org/api/nltk.chat.html
# chatbots _pairs may be useful for some text data, but input is a re pattern which is not compatible
# with current chatterbot
# https://www.smallsurething.com/implementing-the-famous-eliza-chatbot-in-python/
a = nltk.chat
b = a.iesha.iesha_chatbot._pairs
for req, res in b:
  c = re.compile(req)
  print(c.pattern, res)

chat_bot = chatterbot.ChatBot("NUREbot", 
      storage_adapter = "chatterbot.adapters.storage.JsonFileStorageAdapter",
      logic_adapters = ["chatterbot.adapters.logic.MathematicalEvaluation",
        "chatterbot.adapters.logic.TimeLogicAdapter",
        "chatterbot.adapters.logic.ClosestMatchAdapter",])
#chat_bot.set_trainer(chatterbot.trainers.ChatterBotCorpusTrainer)
#chat_bot.train("chatterbot.corpus.english")
chat_bot.set_trainer(chatterbot.trainers.ListTrainer)
# maybe faster is just to train for my functions + additional later
chat_bot.train([
  "аудитория",
  "Используй команду /aud number",
  "ауд",
  "Используй команду /aud number",
  "где аудитория?",
  "Чтобы узнать спроси через команду /aud number",
  "как пройти в аудиторию?",
  "Чтобы узнать спроси через команду /aud number",
  "на каком этаже аудитория?",
  "Чтобы узнать спроси через команду /aud number",
  "в каком корпусе аудитория?",
  "Чтобы узнать спроси через команду /aud number",
  "где находится аудитория",
  "Чтобы узнать спроси через команду /aud number",


  "где столовая?",
  "В главном корпусе : \n" +
    "\n\t на первом этаже нет столовых. Можно найти кофейный аппарат, если сразу после главного входа идти налево" +
    
    "\n\t на втором этаже, если подниматься по главной лестнице, то сразу справа столовая, в которой можно плотно поесть" +
    "\n\t на втором этаже, если подниматься по главной лестнице, то сразу слева небольшая закусочная" +
    "\n\t на втором этаже сразу можно заметить зону отдыха и кофейную точку. Работает с 9:00 до 17:30" +

    "\n\t на третьем этаже нет столовых." +
  
    "\n\t на четвертом этаже нет столовых" +
    
    "\n\t на пятом этаже нет столовых"
])

updater = Updater('259933822:AAGoMk2Fb2YwBP6bOMl69a4E7DDmXBrxtz4')

updater.dispatcher.add_handler(MessageHandler([Filters.text], message_handler))
updater.dispatcher.add_handler(CommandHandler(command = 'aud', callback = auditory, pass_args = True))

updater.start_polling()
updater.idle()