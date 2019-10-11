import logging
import time

import eventlet
import requests
from telegram import Bot, InputMediaPhoto

import config

bot = Bot(token=config.TG_TOKEN, base_url=config.TG_API_URL)


def get_data():
    timeout = eventlet.Timeout(10)
    try:
        feed = requests.get(config.URL_VK)
        return feed.json()
    except eventlet.timeout.Timeout:
        logging.warning('Got Timeout while retrieving VK JSON data. Cancelling...')
        return None
    finally:
        timeout.cancel()


def send_new_posts(items, last_id):
    for item in items:
        if item['id'] <= last_id:
            continue
        msg_caption = item['text'] + f'\n\n{config.GROUP_URL}'
        if len(item['attachments']) > 1:
            imgs = []
            for img in item['attachments']:
                try:
                    imgs.append(InputMediaPhoto(img['photo']['sizes'][-1]['url']))
                except Exception:
                    print(img['audio']['artist'], img['audio']['title'])
            msg_data = bot.send_media_group(config.CHANNEL_NAME, imgs)
            msg_id = msg_data[0]['message_id']
            bot.edit_message_caption(config.CHANNEL_NAME, msg_id, caption=msg_caption)
        else:
            img_url = item['attachments'][0]['photo']['sizes'][-1]['url']
            bot.send_photo(config.CHANNEL_NAME, img_url, msg_caption)
        # на всякий случай
        time.sleep(1)
    return


def check_new_posts_vk():
    logging.info('[VK] Started scanning for new posts')
    with open(config.FILENAME_VK, 'rt') as file:
        last_id = int(file.read())
        if last_id is None:
            logging.error('Could not read from storage. Skipped iteration.')
            return
        logging.info('Last ID (VK) = {!s}'.format(last_id))
    try:
        feed = get_data()
        if feed is not None:
            entries = feed['response']['items']
            send_new_posts(entries, last_id)
            # новый id -> в last_id
            with open(config.FILENAME_VK, 'wt') as file:
                file.write(str(entries[0]['id']))
                logging.info('New last_id (VK) is {!s}'.format((entries[0]['id'])))
    except Exception as ex:
        logging.error('Exception of type {!s} in check_new_post(): {!s}'.format(type(ex).__name__, str(ex)))
        if type(ex).__name__ == 'TimedOut':
            with open(config.FILENAME_VK, 'wt') as file:
                feed = get_data()
                entries = feed['response']['items']
                file.write(str(entries[0]['id']))
                logging.info('New last_id (VK) is {!s}'.format((entries[0]['id'])))
    logging.info('[VK] Finished scanning')
    return


if __name__ == '__main__':
    logging.getLogger('requests').setLevel(logging.CRITICAL)
    logging.basicConfig(format='[%(asctime)s] %(filename)s:%(lineno)d %(levelname)s - %(message)s', level=logging.INFO,
                        filename='bot_log.log', datefmt='%d.%m.%Y %H:%M:%S')
    SINGLE_RUN = 0

    if not SINGLE_RUN:
        while True:
            check_new_posts_vk()
            # пауза 30 мин
            logging.info('[App] Script went to sleep.')
            time.sleep(60*30)
    else:
        check_new_posts_vk()
    logging.info('[App] Script exited.\n')
