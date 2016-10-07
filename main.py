from telegram.ext import Updater, CommandHandler
import chatterbot
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

chat_bot = None

def start(bot, update):
    update.message.reply_text('Bot is now in English. A multi-language too')

def hello(bot, update):
    update.message.reply_text(
        'Hello {}'.format(update.message.from_user.first_name)
    )

def function():
    passdef

chat_bot = chatterbot.ChatBot(
      "NUREbot", 
      storage_adapter="chatterbot.adapters.storage.JsonFileStorageAdapter",
      logic_adapters=[
        "chatterbot.adapters.logic.MathematicalEvaluation",
        "chatterbot.adapters.logic.TimeLogicAdapter",
        "chatterbot.adapters.logic.ClosestMatchAdapter",
      ]
    )
chat_bot.set_trainer(chatterbot.trainers.ChatterBotCorpusTrainer)
chat_bot.train("chatterbot.corpus.english")

updater = Updater('259933822:AAGoMk2Fb2YwBP6bOMl69a4E7DDmXBrxtz4')

updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('hello', hello))

updater.start_polling()
updater.idle()