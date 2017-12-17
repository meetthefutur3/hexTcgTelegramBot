import telegram
from telegram.ext import CommandHandler, Filters, Updater, MessageHandler
import logging
import time
import csv
import hashlib,base64
import pymongo
from pymongo import MongoClient
from bson import json_util
from datetime import datetime, timedelta
import standings

userFile = "userDict.csv"
botApiToken = "458333441:AAG4-XSPjb-69dDD8b07TDcyZPs90USYKLs"
dbclient = MongoClient('localhost', 27017)
db = dbclient['HEXREM']
userDictionary = db['dict_users']
botLog = db['bot_log']
tournamentData = db['tournament_data']

logging.basicConfig(filename='hxreBotHandler2.log',level=logging.INFO,format='%(asctime)s %(message)s')
logger = logging.getLogger('botHandler')

def logMessage(message):
    logger.info("-------Api message start------")
    logger.info(message)
    logger.info("-------Api message end------")

    msgDict = message.to_dict()
    msgDict["timestamp"] = datetime.now()
    botLog.insert_one(msgDict)


# Генерим юзера, либо напоминаем ему его код
def start(bot, update):
    logMessage(update.message)
    chatType = update.message.chat.type
    if chatType !="private":
         bot.send_message(chat_id=update.message.chat_id, text="Ненене, никаких групповых чатов")
         return

    chatid = update.message.chat_id
    if(update.message.from_user.first_name):
        fname = update.message.from_user.first_name
    else:
        fname = "John"

    if(update.message.from_user.last_name):
        lname = update.message.from_user.last_name
    else:
        lname = "Doe"

    hashstring = str(chatid) + fname + lname
    apicode = hashlib.md5(hashstring.encode('utf8')).hexdigest()

    userExists = 0
    userApiCode = ""

    userRecord = userDictionary.find_one({"chatId": str(chatid)})

    if not (userRecord):
        #Не нашли - надо делать нового
        userDictionary.insert_one({"chatId":str(chatid),"hexApiCode":apicode,"enableNotifications":"N","firstName":fname,"lastName":lname})
        messageText = ""
        messageText = messageText + "Добро пожаловать. Что бы это чудо работало, в ваш api.ini нужно добавить следующую строку: \nhttp://77.244.213.29:7980?rkey=" + apicode + "|GameStarted|Tournament|GameEnded"
        messageText = messageText + "\nЕсли вы копируете окольными путями через телефон - вертикальные разделители в процессе могут превратиться в что-то типа %124 - замените обратно руками"
        messageText = messageText + "\nПо умолчанию напоминания отключены - введите /enable что бы их включить и /disable что бы выключить обратно"
        messageText = messageText + "\nНу и традиционно  - /help как напоминалка"

        bot.send_message(chat_id=update.message.chat_id, text=messageText)
    else:
        #Напоминаем про апиключ
        messageText = ""
        messageText = messageText + "Напоминаю строку, которую надо добавить api.ini: \nhttp://77.244.213.29:7980?rkey=" + apicode + "|GameStarted|Tournament|GameEnded"
        messageText = messageText + "\nЕсли вы копируете окольными путями через телефон - вертикальные разделители в процессе могут превратиться в что-то типа %124 - замените обратно руками"
        if (userRecord['enableNotifications']=="Y"):
            messageText = messageText + "\nУведомления включены. Что бы отключить - введите /disable"
        else:
            messageText = messageText + "\nУведомления отключены. Что бы включить - введите /enable"
        messageText = messageText + "\nНу и традиционно  - /help как напоминалка"

        bot.send_message(chat_id=update.message.chat_id, text=messageText)

# Включаем уведомлялки
def enable(bot, update):
    logMessage(update.message)

    chatType = update.message.chat.type
    if chatType !="private":
        bot.send_message(chat_id=update.message.chat_id, text="Ненене, никаких групповых чатов")
        return

    chatid = update.message.chat_id
    userRecord = userDictionary.find_one({"chatId": str(chatid)})

    if not (userRecord):
        #Иди регайся
        messageText = ""
        messageText = messageText + "А ты вообще кто такой? Иди пиши /start"
        bot.send_message(chat_id=update.message.chat_id, text=messageText)
    else:
        userDictionary.update_one({"chatId": str(chatid)},{'$set':{"enableNotifications":"Y"}})
        bot.send_message(chat_id=update.message.chat_id, text="Напоминания включены")

def disable(bot, update):
    logMessage(update.message)
    chatType = update.message.chat.type
    if chatType !="private":
        bot.send_message(chat_id=update.message.chat_id, text="Ненене, никаких групповых чатов")
        return

    chatid = update.message.chat_id
    userRecord = userDictionary.find_one({"chatId": str(chatid)})

    if not (userRecord):
        #Иди регайся
        messageText = ""
        messageText = messageText + "А ты вообще кто такой? Иди пиши /start"
        bot.send_message(chat_id=update.message.chat_id, text=messageText)
    else:
        userDictionary.update_one({"chatId": str(chatid)},{'$set':{"enableNotifications":"N"}})
        bot.send_message(chat_id=update.message.chat_id, text="Напоминания отключены")

def help(bot, update):
    logMessage(update.message)
    chatType = update.message.chat.type
    if chatType !="private":
        bot.send_message(chat_id=update.message.chat_id, text="Ненене, никаких групповых чатов")
        return

    chatid = update.message.chat_id
    userRecord = userDictionary.find_one({"chatId": str(chatid)})

    if not (userRecord):
        #Иди регайся
        messageText = ""
        messageText = messageText + "Не знаю, кто ты такой, так что лучше начни с команды /start"
        bot.send_message(chat_id=update.message.chat_id, text=messageText)
    else:
        apicode = userRecord['hexApiCode']
        messageText = ""
        messageText = messageText + "Что бы это чудо работало, в ваш api.ini нужно добавить следующую строку: \nhttp://77.244.213.29:7980?rkey=" + apicode + "|GameStarted|Tournament|GameEnded"
        messageText = messageText + "\nЕсли вы копируете окольными путями через телефон - вертикальные разделители в процессе могут превратиться в что-то типа %124 - замените обратно руками"
        messageText = messageText + "\nЛучше запускать телеграм на ПК - встречались проблемы у тех, у кого телеграм был только на телефоне (напоминалки приходили с задержкой)"
        messageText = messageText + "\nО багах можно писать в @meetthefutur3 - но исправлять их я, скорее всего, буду долго"
        messageText = messageText + "\n/enable - включить напоминалки"
        messageText = messageText + "\n/disable - выключить напоминалки"
        messageText = messageText + "\nЕсли есть предложения по улучшению - велком"

        bot.send_message(chat_id=update.message.chat_id, text=messageText)

def unknown(bot, update):
    logMessage(update.message)
    chatType = update.message.chat.type
    if chatType !="private":
        bot.send_message(chat_id=update.message.chat_id, text="Ненене, никаких групповых чатов")
        return
    bot.send_message(chat_id=update.message.chat_id, text="Не знаю такого. Пиши /help")

def stds(bot, update, args):
    #{"timestamp" : { $lte : new Date(ISODate().getTime() - 1000 * 3600 * 24 * 3)}}
    tournamentID = ' '.join(args)

    if(tournamentID):
        st = standings.get_info(tournamentID)
        msgText = '```\n' + str('\n'.join(st[:32])) + '\n```'
        bot.send_message(chat_id=update.message.chat_id, text=msgText,  parse_mode=telegram.ParseMode.MARKDOWN)
        # Call standings with ID = arg
    else:
        recentTournaments = tournamentData.find({"timestamp" : { "$gte" : datetime.now() - timedelta(hours=4)}})

        if(recentTournaments.count() == 0):
            #say "no recent, use ID if you want to find old"
            pass
        elif(recentTournaments.count() >1):
            msgText = "```\nThere is more than one recent tournament. Use /standings [tournament ID]. Recent tournament options:"
            for rt in recentTournaments:
                msgText+=('\n{} | Tournament ID: {} | Last update: {}'.format(rt["FormatReadable"], rt["_id"], rt["timestamp"]))
            msgText+=("\n```")
            bot.send_message(chat_id=update.message.chat_id, text=msgText,  parse_mode=telegram.ParseMode.MARKDOWN)
            #return choice of HiddenShadow
        else:
            st = standings.get_info(recentTournaments[0]["_id"])
            msgText = '```\n' + str('\n'.join(st[:32])) + '\n```'
            bot.send_message(chat_id=update.message.chat_id, text=msgText,  parse_mode=telegram.ParseMode.MARKDOWN)
            #Call standings with ID = recentTournaments["_id"]

def tournaments(bot, update):
    tournamentList = tournamentData.find().sort('timestamp', pymongo.DESCENDING)[:10]
    if(tournamentList):
        msgText = "```\nRecent tournaments list. Use /standings [tournament ID] to see the standings:"
        for rt in tournamentList:
            msgText+=('\n{} | Tournament ID: {} | Last update: {}'.format(rt["FormatReadable"], rt["_id"], rt["timestamp"]))
        msgText+=("\n```")
        bot.send_message(chat_id=update.message.chat_id, text=msgText,  parse_mode=telegram.ParseMode.MARKDOWN)

def exterminate(bot, update, args):
    tournamentID = ' '.join(args)
    if(tournamentID):
        result = tournamentData.delete_one({"_id" : tournamentID})
        if (result.deleted_count > 0) :
            bot.send_message(chat_id=update.message.chat_id, text="Done")
        else:
            bot.send_message(chat_id=update.message.chat_id, text="Nothing deleted")

bot = telegram.Bot(token=botApiToken)
print(bot.get_me())

updater = Updater(token=botApiToken)
dispatcher = updater.dispatcher

#handlers
start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

enable_handler = CommandHandler('enable', enable)
dispatcher.add_handler(enable_handler)

disable_handler = CommandHandler('disable', disable)
dispatcher.add_handler(disable_handler)

help_handler = CommandHandler('help', help)
dispatcher.add_handler(help_handler)

stds_handler = CommandHandler('standings', stds, pass_args=True)
dispatcher.add_handler(stds_handler)

exrerminate_handler = CommandHandler('exterminate', exterminate, pass_args=True)
dispatcher.add_handler(exrerminate_handler)

tournaments_handler = CommandHandler('tournaments', tournaments)
dispatcher.add_handler(tournaments_handler)

unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(unknown_handler)
#end handlers

updater.start_polling()

updater.idle()


# >>> def caps(bot, update, args):
# ...     text_caps = ' '.join(args).upper()
# ...     bot.send_message(chat_id=update.message.chat_id, text=text_caps)
# ...
# >>> caps_handler = CommandHandler('caps', caps, pass_args=True)
# >>> dispatcher.add_handler(caps_handler)
