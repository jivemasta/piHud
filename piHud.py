#piHud Main file
#this will display bitcoin price, weather, and tindie orders on a eInk display on a raspberry pi

import requests
import json
import time
import threading
from PIL import Image, ImageDraw, ImageFont
import logging

logging.basicConfig(level=logging.DEBUG,format='[%(asctime)s][%(levelname)s] (%(threadName)-10s) %(message)s',)

ticks = 0
btcPrice = 0
tindieOrders = []
weather = {}

def GetBTCPrice():
    logging.debug('Getting BTC Price')

    global btcPrice

    #kraken API URL, don't exceed more than 1 call/second
    bitcoinApiUrl = "https://api.kraken.com/0/public/Ticker"
    btcResponse = requests.get(bitcoinApiUrl,{'pair':'BTCUSD'})
    btcResponseJson = btcResponse.json()
    btcPrice = float(btcResponseJson['result']['XXBTZUSD']['c'][0])

    logging.debug('Done Getting BTC Price')

def GetTindieOrders():
    logging.debug("Getting Tindie Orders")
        # ORDERS JSON FORMAT
        # 'company_title': '',
        # 'date': '2021-03-02T01:41:54.108556',
        # 'date_shipped': None,
        # 'discount_code': '',
        # 'email': 'zoe.dewitt@gmx.at',
        # 'items': 
        #     'model_number': '',
        #     'options': '', 
        #     'pre_order': False, 
        #     'price_total': 20.0, 
        #     'price_unit': 20.0, 
        #     'product': "Black Panel for Pam's New Workout", 
        #     'quantity': 1, 
        #     'sku': '20776', 
        #     'status': 'billed',
        # 'message': '',
        # 'number': 249527,
        # 'payment': 'unpaid',
        # 'phone': '+436506848455',
        # 'refunded': False,
        # 'shipped': False,
        # 'shipping_city': 'Vienna',
        # 'shipping_country': 'Austria',
        # 'shipping_country_code': 'AT',
        # 'shipping_instructions': '',
        # 'shipping_name': 'Michael Zoe Dewitt',
        # 'shipping_postcode': '1070',
        # 'shipping_service': 'United States Postal Service Standard Ground Rate',
        # 'shipping_state': 'Vienna',
        # 'shipping_street': 'Hermanngasse 31/18',
        # 'total': 33.68,
        # 'total_ccfee': 1.32,
        # 'total_discount': '0',
        # 'total_kickback': 0.0,
        # 'total_seller': 31.93,
        # 'total_shipping': 15.0,
        # 'total_subtotal': 35.0,
        # 'total_tindiefee': 1.75,
        # 'tracking_code': None,
        # 'tracking_url': ''
    global tindieOrders

    #API Key info for tindie account
    tindieApiUser = "jivemasta"
    tindieApiKey = "c89458aa11ed4e8f21456dd036630c095098641e"
    tindieApiUrl = "/api/v1/order/?format=json&username=" + tindieApiUser + "&api_key=" + tindieApiKey

    #Variables
    orderList = []
    moreOrders = True

    #loops through api calls until it gets to the end of the list adding each batch to the orderList
    #will go through at least once to get list, then check the meta object to see if there is a URL to the next list
    while moreOrders == True:
        #starts with the base API URL, but will get updated to the next list URL at the end of each loop
        tindieResponse = requests.get('https://www.tindie.com' + tindieApiUrl,{'limit':'50'})

        #Convert response to JSON Object and add orders to orderList
        tindieJSON = tindieResponse.json()
        orderList +=  tindieJSON['orders']

        #The API adds a URL to the next chunk of the order list in the meta object
        #If it has something, make that the next API URL and loop around, otherwise leave the loop
        if tindieJSON['meta']['next'] != None:
            moreOrders = True
            tindieApiUrl = tindieJSON['meta']['next']
        else:
            moreOrders = False
    #return the entire list of orders 
    tindieOrders = orderList

    logging.debug("Done Getting Tindie Orders")

def GetWeather():
    logging.debug('Getting Weather')

    #for JSON structure
    #https://openweathermap.org/api/one-call-api

    global weather

    #lat and lon for the house
    lat = 41.060488965115056
    lon = -83.7288217363699
    units = 'imperial'

    #set up API URL
    apiKey = '4a2cf1128f138c25aa3d062c068700ad'
    weatherApiUrl = f'https://api.openweathermap.org/data/2.5/onecall?lat={lat}&lon={lon}&units={units}&appid={apiKey}'

    #get weather as a JSON object
    weatherResponse = requests.get(weatherApiUrl)
    weather = weatherResponse.json()

    logging.debug('Done Getting Weather')



def UpdateData():
    global btcPrice
    global tindieOrders

    btcThread = threading.Thread(target=GetBTCPrice)
    tindieThread = threading.Thread(target=GetTindieOrders)
    weatherThread = threading.Thread(target=GetWeather)

    btcThread.start()
    tindieThread.start()
    weatherThread.start()

    btcThread.join()
    tindieThread.join()
    weatherThread.join()

def RenderImage():
    global btcPrice

    white = (255,255,255)
    black = (0,0,0)
    red = (255,0,0)

    #create a new image file to put on the display
    #display is 400x300 with 3 colors white, red, and black
    out = Image.new('RGB',(400,300),(255,255,255))
    #load default font
    font = ImageFont.truetype('arial.ttf',size=14)
    #create the drawing object
    draw = ImageDraw.Draw(out)

    #draw bitcoin price
    draw.text((0,0),f'Bitcoin: {btcPrice:.2f}',fill=black,font=font)

    #draw weather
    temp = weather['current']['temp']
    draw.text((0,30),f'Temp: {temp}',fill=black,font=font)

    unshippedOrders = 0
    for order in tindieOrders:
        if order['shipped'] == False:
            unshippedOrders +=1
    draw.text((0,60),f'Unshipped Orders: {unshippedOrders}',fill=black,font=font)

    out.show()


while(1):
    UpdateData()

    # for order in tindieOrders:
    #     if order['shipped'] == False:
    #         items = []
    #         for item in order['items']:
    #             items.append(item['product'])
    #         print("Ship out {} to {} in {}".format(items.__str__(),order['shipping_name'],order['shipping_country']))

    RenderImage()
    time.sleep(10)