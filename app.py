from __future__ import unicode_literals

import os
import sys
import redis
import requests
from bs4 import BeautifulSoup

from argparse import ArgumentParser
from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookParser,
)
from linebot.exceptions import (
    InvalidSignatureError
)

from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageMessage, VideoMessage, FileMessage, StickerMessage,
    LocationMessage, MessageAction, QuickReply, QuickReplyButton, LocationAction,
    ImageSendMessage, ImageCarouselTemplate, ConfirmTemplate, PostbackTemplateAction, LocationSendMessage,
    CarouselColumn, ImageCarouselColumn, URITemplateAction, TemplateSendMessage,
    CarouselTemplate, FollowEvent, MessageTemplateAction,
    ButtonsTemplate,
)
# from googletrans import Translator
# translator = Translator()
import googlemaps

gmaps = googlemaps.Client(key='AIzaSyBDOCnNog_WEQ0zQWMIoBiXqqmmMbmTc90')

HOST = "redis-11209.c99.us-east-1-4.ec2.cloud.redislabs.com"
PWD = "V6rZfXZodkAWI51gaILJvj4eCXHrT6VS"
PORT = "11209"
pool = redis.ConnectionPool(host=HOST, password=PWD, port=PORT, decode_responses=True)
r = redis.Redis(connection_pool=pool)
app = Flask(__name__)
# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
# obtain the port that heroku assigned to this app.
heroku_port = os.getenv('PORT', None)

if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
parser = WebhookParser(channel_secret)


@app.route("/callback", methods=['POST'])
def callback():
    global events
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # parse webhook body
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)

    # if event is MessageEvent and message is TextMessage, then echo text
    for event in events:
        if isinstance(event, FollowEvent):
            handel_greeting(event)
        if not isinstance(event, MessageEvent):
            continue
        if isinstance(event.message, TextMessage):
            handle_TextMessage(event)
        if isinstance(event.message, ImageMessage):
            handle_ImageMessage(event)
        if isinstance(event.message, VideoMessage):
            handle_VideoMessage(event)
        if isinstance(event.message, FileMessage):
            handle_FileMessage(event)
        if isinstance(event.message, StickerMessage):
            handle_StickerMessage(event)
        if isinstance(event.message, LocationMessage):
            handle_LocationMessage(event)
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue
    return 'OK'

    # for msg in msgs:
    #     translateCN(msg)
    # return 'OK'


#
#
# def Languages():
#     buttons_template = ButtonsTemplate(text='Languages', actions=[
#         MessageTemplateAction(label='English'),
#         MessageTemplateAction(label='中文'),
#     ])
#     template_message = TemplateSendMessage(
#         alt_text='languages',
#         template=buttons_template)
#     return template_message
#
#
# def translateCN(text):
#     text1 = translator.translate(str(text),  dest='zh-cn').text
#     return text1


def handel_greeting(event):
    line_bot_api.reply_message(
        event.reply_token, [
            TextSendMessage(
                text='Hello! This is your healthcare chatbot\uDBC0\uDC8D.'
                # 'Please choose your prefer languages:\n你好，这是你的健康小助手\uDBC0\uDC8D，请选择你的语言：'
            ),
            # Languages(),
            MainMenu(),
        ])


def prepareTitle(text):
    result = text[:37] + "..." if len(text) > 40 else text
    result = "{}".format(result)
    return result


def getPrecaution():
    buttons_template = ButtonsTemplate(text='Precautions:', actions=[
        MessageTemplateAction(label='Wash your hand', text='Wash your hand'),
        MessageTemplateAction(label='Protect others', text='Protect others'),
    ])
    template_message = TemplateSendMessage(
        alt_text='Precautions', template=buttons_template)
    return template_message


def getMoreKnowledge():
    result = []
    res = requests.get('https://www.who.int/emergencies/diseases/novel-coronavirus-2019/advice-for-public/videos')
    soup = BeautifulSoup(res.text, 'html.parser')
    videos = soup.find('div', attrs={'id': 'PageContent_C054_Col01'})
    for num in range(0, 5):
        url = videos.select('iframe')[num]['src']
        soup_url = BeautifulSoup(requests.get(url).text, 'html.parser')
        title = prepareTitle(soup_url.title.text)
        column = CarouselColumn(
            title=title,
            text='views:' + str(r.incr(title)),
            actions=[
                URITemplateAction(
                    label='More',
                    uri=url
                ),
            ]
        )
        result.append(column)

    carousel = TemplateSendMessage(
        alt_text="5 more pieces of knowledge",
        template=CarouselTemplate(
            columns=result
        )
    )
    result_text = 'Find more videos about coronavirus, please click: ' \
                  'https://www.who.int/emergencies/diseases/novel-coronavirus-2019/advice-for-public/videos '
    result = [carousel, TextSendMessage(text=result_text)]
    return result


def getReport():
    res = requests.get('https://www.who.int/emergencies/diseases/novel-coronavirus-2019/situation-reports')
    soup = BeautifulSoup(res.text, 'html.parser')
    sreport = soup.find_all('a', attrs={'target': '_blank'})[5]
    report = str('https://www.who.int' + sreport['href'])
    return report


def getNews():
    result = []
    res = requests.get('https://www.who.int/news-room/releases')
    soup = BeautifulSoup(res.text, 'html.parser')
    news = soup.find_all('a', {'class': 'link-container'}, limit=5)
    for t in news:
        value = t.attrs
        title = value['aria-label']
        url = 'https://www.who.int/' + value['href']
        column = CarouselColumn(
            title=prepareTitle(title),
            text='views:' + str(r.incr(title)),
            actions=[URITemplateAction(
                label='More',
                uri=url
            )]
        )
        result.append(column)

    carousel = TemplateSendMessage(
        alt_text="5 latest news",
        template=CarouselTemplate(
            columns=result
        )
    )
    result_text = 'Find more information about coronavirus, please click: ' \
                  'https://www.who.int/emergencies/diseases/novel-coronavirus-2019 '
    result = [carousel, TextSendMessage(text=result_text)]
    return result


def getMythBusters():
    result = []
    res = requests.get(
        'https://www.who.int/emergencies/diseases/novel-coronavirus-2019/advice-for-public/myth-busters')
    soup = BeautifulSoup(res.text, 'html.parser')
    myths = soup.find('div', attrs={'id': 'PageContent_C003_Col01'})
    for num in range(1, 6):
        myths_image = myths.select('.link-container')[num]
        url = myths_image['href']
        column = ImageCarouselColumn(
            image_url=str(url),
            action=URITemplateAction(label='Details', uri=url))
        result.append(column)
    carousel = TemplateSendMessage(
        alt_text="5 myth busters",
        template=ImageCarouselTemplate(
            columns=result
        )
    )
    result_text = 'Find more information about myth busters, please click: ' \
                  'https://www.who.int/emergencies/diseases/novel-coronavirus-2019/advice-for-public/myth-busters '
    result = [carousel, TextSendMessage(text=result_text)]
    return result


def getDonate():
    carousel = TemplateSendMessage(
        alt_text="Donate",
        template=ButtonsTemplate(
            title='Help Fight Coronavirus',
            text='This donation is for COVID-19 Solidarity Response Fund',
            actions=[URITemplateAction(
                label='Go to donate',
                uri='https://covid19responsefund.org/'
            )]
        )
    )
    result_text = 'Attention! This donation is from WHO(World Health Organization) and has nothing to do with the ' \
                  'chatbot, find more information please click: ' \
                  'https://www.who.int/emergencies/diseases/novel-coronavirus-2019/donate '
    result = [TextSendMessage(text=result_text), carousel]
    return result


def MainMenu():
    buttons_template = ButtonsTemplate(text='Main services', actions=[
        MessageTemplateAction(label='1 Popular Science', text='Popular science'),
        MessageTemplateAction(label='2 Outbreak News', text='Outbreak news'),
        MessageTemplateAction(label='3 Emergency & Donate', text='Emergency & Donate'),
    ])
    template_message = TemplateSendMessage(
        alt_text='Menu', template=buttons_template)
    return template_message


def Menu1():
    buttons_template = ButtonsTemplate(text='1 Popular science', actions=[
        MessageTemplateAction(label='Precaution', text='Precaution'),
        MessageTemplateAction(label='More Knowledge', text='More knowledge'),
        MessageTemplateAction(label='Main Menu', text='Menu'),
    ])
    template_message = TemplateSendMessage(
        alt_text='Menu1', template=buttons_template)
    return template_message


def Menu2():
    buttons_template = ButtonsTemplate(text='2 News about COVID-2019', actions=[
        MessageTemplateAction(label='Situation Report', text='Situation report'),
        MessageTemplateAction(label='Latest News', text='Latest news'),
        MessageTemplateAction(label='Myth Busters', text='Myth busters'),
        MessageTemplateAction(label='Main Menu', text='Menu'),
    ])
    template_message = TemplateSendMessage(
        alt_text='Menu2', template=buttons_template)
    return template_message


def Menu3():
    buttons_template = ButtonsTemplate(text='Emergency & Donate', actions=[
        MessageTemplateAction(label='Find Hospital', text='Find hospital'),
        MessageTemplateAction(label='Donate', text='Donate'),
        MessageTemplateAction(label='Main Menu', text='Menu'),
    ])
    template_message = TemplateSendMessage(
        alt_text='Menu3', template=buttons_template)
    return template_message


def handle_TextMessage(event):
    print(event.message.text)
    if event.message.text == 'Menu':
        msg = 'This is main menu: '
        menu = MainMenu()
        line_bot_api.reply_message(
            event.reply_token, [
                TextSendMessage(msg),
                menu]
        )
    elif event.message.text == 'Popular science':
        msg = 'This is popular Science knowledge about COVID-2019, what kinds of information you want to know?'
        menu = Menu1()  # Menu1
        line_bot_api.reply_message(
            event.reply_token, [
                TextSendMessage(msg),
                menu]
        )
    elif event.message.text == 'Precaution':
        line_bot_api.reply_message(
            event.reply_token, getPrecaution()
        )
    elif event.message.text == 'More knowledge':
        line_bot_api.reply_message(
            event.reply_token, getMoreKnowledge())
    elif event.message.text == 'Wash your hand':
        line_bot_api.reply_message(
            event.reply_token, [
                ImageSendMessage(
                    original_content_url='https://www.who.int/images/default-source/health-topics/coronavirus/social'
                                         '-media-squares/blue-1.tmb-1920v.png?sfvrsn=3d15aa1c_1 ',
                    preview_image_url='https://www.who.int/images/default-source/health-topics/coronavirus/social'
                                      '-media-squares/blue-1.tmb-1920v.png?sfvrsn=3d15aa1c_1 '
                ),
                ImageSendMessage(
                    original_content_url='https://www.who.int/images/default-source/health-topics/coronavirus/social'
                                         '-media-squares/blue-2.tmb-1920v.png?sfvrsn=2bc43de1_1 ',
                    preview_image_url='https://www.who.int/images/default-source/health-topics/coronavirus/social'
                                      '-media-squares/blue-2.tmb-1920v.png?sfvrsn=2bc43de1_1 '
                ),
            ])
    elif event.message.text == 'Protect others':
        line_bot_api.reply_message(
            event.reply_token, [
                ImageSendMessage(
                    original_content_url='https://www.who.int/images/default-source/health-topics/coronavirus/social'
                                         '-media-squares/blue-3.tmb-1920v.png?sfvrsn=b1ef6d45_1',
                    preview_image_url='https://www.who.int/images/default-source/health-topics/coronavirus/social'
                                      '-media-squares/blue-3.tmb-1920v.png?sfvrsn=b1ef6d45_1'),
                ImageSendMessage(
                    original_content_url='https://www.who.int/images/default-source/health-topics/coronavirus/social'
                                         '-media-squares/blue-4.tmb-1920v.png?sfvrsn=a5317377_5',
                    preview_image_url='https://www.who.int/images/default-source/health-topics/coronavirus/social'
                                      '-media-squares/blue-4.tmb-1920v.png?sfvrsn=a5317377_5')
            ])
    elif event.message.text == 'Outbreak news':
        msg = 'This is the latest news about COVID-2019, what kinds of information you want to know? '
        menu = Menu2()  # Menu2
        line_bot_api.reply_message(
            event.reply_token, [
                TextSendMessage(msg),
                menu]
        )
    elif event.message.text == 'Situation report':
        msg1 = 'This is the latest situation report, please click:' + getReport()
        msg2 = 'Find more reports please click: https://www.who.int/emergencies/diseases/novel-coronavirus-2019' \
               '/situation-reports '
        line_bot_api.reply_message(
            event.reply_token, [
                TextSendMessage(msg1),
                TextSendMessage(msg2)])
    elif event.message.text == 'Latest news':
        line_bot_api.reply_message(
            event.reply_token, getNews())
    elif event.message.text == 'Myth busters':
        line_bot_api.reply_message(
            event.reply_token, getMythBusters())
    elif event.message.text == 'Emergency & Donate':
        line_bot_api.reply_message(
            event.reply_token, Menu3())
    elif event.message.text == 'Find hospital':
        msg = 'Please send your location, thanks.'
        line_bot_api.reply_message(event.reply_token, TextSendMessage(
            text=msg,
            quick_reply=QuickReply(items=[QuickReplyButton(
                action=LocationAction(label='Send your location'),
                )])))
    elif event.message.text == 'Donate':
        line_bot_api.reply_message(
            event.reply_token, getDonate()
        )
    else:
        msg = "Sorry! I don't understand. What kind of the following information you want to know?"
        line_bot_api.reply_message(
            event.reply_token, [TextSendMessage(
                text=msg,
                quick_reply=QuickReply(items=[
                    QuickReplyButton(action=MessageAction(
                        label='1 Popular Science',
                        text='Popular science')),
                    QuickReplyButton(action=MessageAction(
                        label='2 Outbreak News',
                        text='Outbreak news')),
                    QuickReplyButton(action=MessageAction(
                        label='3 Emergency & Donate',
                        text='Emergency & Donate')),
                ]))]
        )


def handle_LocationMessage(event):
    r.set('my_lat', event.message.latitude)
    r.set('my_lon', event.message.longitude)
    mylat = float(r.get('my_lat'))
    mylng = float(r.get('my_lon'))
    mylocation = '{}, {}'.format(mylat, mylng)
    places_results = gmaps.places_nearby(location=mylocation, type='hospital', radius=10000)
    list = []
    for place in places_results['results']:
        name = place['name']
        lat = place['geometry']['location']['lat']
        lng = place['geometry']['location']['lng']
        address = place['vicinity']
        distance = ((lat - mylat) ** 2 + (lng - mylng) ** 2) ** 0.5
        info = distance, name, lat, lng, address
        list.append(info)
    list.sort()
    name_ = list[0][1]
    lat_ = list[0][2]
    lng_ = list[0][3]
    address_ = list[0][4]
    result_text = 'The nearest hospital around you is ' + name_ + '.'
    result = [TextSendMessage(text=result_text),
              LocationSendMessage(
                  title=name_, address=address_,
                  latitude=lat_, longitude=lng_)]
    line_bot_api.reply_message(event.reply_token, result)


# Handler function for Sticker Message
def handle_StickerMessage(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="Nice sticker!")
    )


# Handler function for Image Message
def handle_ImageMessage(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="Nice image!")
    )


# Handler function for Video Message
def handle_VideoMessage(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="Nice video!")
    )


# Handler function for File Message
def handle_FileMessage(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="Nice file!")
    )


if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    app.run(host='0.0.0.0', debug=options.debug, port=heroku_port)
