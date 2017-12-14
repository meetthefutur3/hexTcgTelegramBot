#!/usr/bin/python3

import socket
import logging
import json
import ssl
import requests
import hashlib,base64
import time
from random import randint
from urllib.parse import urlparse,parse_qs
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pymongo import MongoClient
from bson import json_util
from datetime import datetime

#datetime.now().strftime('%Y-%m-%d %H:%M:%S')

hostName = ""
hostPort = 7980
botApiToken = "458333441:AAG4-XSPjb-69dDD8b07TDcyZPs90USYKLs"

dbclient = MongoClient('localhost', 27017)
db = dbclient['HEXREM']
userDictionary = db['dict_users']
apiLog = db['api_log']
tournamentData = db['tournament_data']

class apiHandleServer(SimpleHTTPRequestHandler):

    def _set_headers(self):
        self.send_header('Content-type', 'text/html')
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        self.send_header('Content-type', 'application/json')
        self.send_response(200, "{}")
        self.wfile.write("{}".encode("utf-8"))
        self.end_headers()
        query_components = parse_qs(urlparse(self.path).query)
        rkey = query_components["rkey"]
        logger.info("-------Api message start------")
        logger.info(rkey)
        logger.info(post_data.decode("utf-8"))
        logger.info("-------Api message end------")

        userkey = rkey[0]
        chatId = 0

        jsdata = json.loads(post_data)

        apiLogData = json_util.loads(post_data)

        apiLogData["apikey"] = userkey
        # apiLogData["timestampstr"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        apiLogData["timestamp"] = datetime.now()

        gamesFinished = 0

        if(apiLogData["Message"]=="Tournament"):
        #Fix: Mongo doesnt accept huge integers which are in tournament IDs
            apiLogData["TournamentData"]["ID"] = str(apiLogData["TournamentData"]["ID"])
            for g in apiLogData["TournamentData"]["Games"]:
                g["ID"]=str(g["ID"])
                if(g["GameOneWinner"] != "" ):
                    gamesFinished += 1
                if(g["GameTwoWinner"] != "" ):
                    gamesFinished += 1
                if(g["GameThreeWinner"] != "" ):
                    gamesFinished += 1

        # print(gamesFinished)

        apiLog.insert_one(apiLogData)

        msgtype = jsdata["Message"]

        if(msgtype == "GameStarted"):
            # =START= Game Start notification
            userRecord = userDictionary.find_one({"hexApiCode": userkey})

            if not (userRecord):
                logger.info("user not found")
                return

            if (userRecord['enableNotifications']=="N"):
                logger.info("notifications are disabled")
                return

            chatId = userRecord['chatId']

            outMessage = "Your game have started!"

            restCallUrl = "https://api.telegram.org/bot"
            restCallUrl = restCallUrl + botApiToken
            restCallUrl = restCallUrl + "/sendMessage?chat_id="
            restCallUrl = restCallUrl + str(chatId)
                #restCallUrl = restCallUrl + "44156117"
            restCallUrl = restCallUrl + "&text=" + outMessage

            time.sleep(randint(0,10))

            logger.info("Sent mesage to chat" + str(chatId))
            logger.info(restCallUrl)
            response = requests.post(restCallUrl)
        # =END= Game Start notification
        elif(msgtype == "Tournament"):
        #=START= Handling tournament info
            if(apiLogData["TournamentData"]["Style"] == 1):
                #and apiLogData["TournamentData"]["Games"]):
                #style:1 = scheduled
                existingRecord = tournamentData.find_one({"TournamentData.ID": apiLogData["TournamentData"]["ID"]})

                if(not existingRecord or existingRecord["GameNumber"] < gamesFinished):
                    apiLogData["_id"] = apiLogData["TournamentData"]["ID"]
                    if(apiLogData["TournamentData"]["Format"] == 0):
                        apiLogData["FormatReadable"] = "Bash"
                    elif(apiLogData["TournamentData"]["Format"] == 65):
                        apiLogData["FormatReadable"] = "Clash"
                    else:
                        apiLogData["FormatReadable"] = "Random"

                    apiLogData["GameNumber"] = gamesFinished

                    tournamentData.replace_one({'TournamentData.ID':apiLogData["TournamentData"]["ID"]},apiLogData,True)
        #=END= Handling tournament info


#set up logger
logger = logging.getLogger('apiHandler')
logging.basicConfig(filename='hxreApiHandler2.log',level=logging.INFO,format='%(asctime)s %(message)s')

#start server
apiHandleServer = HTTPServer((hostName, hostPort), apiHandleServer)
#apiHandleServer.socket = ssl.wrap_socket (apiHandleServer.socket, keyfile='futurePrivate.key', certfile='futurePublic.pem', server_side=True)

logger.info("Server Starts - %s:%s" % (hostName, hostPort))
print(time.asctime(), "Server Starts - %s:%s" % (hostName, hostPort))

try:
    apiHandleServer.serve_forever()
except KeyboardInterrupt:
    pass

apiHandleServer.server_close()
print(time.asctime(), "Server Stops - %s:%s" % (hostName, hostPort))
