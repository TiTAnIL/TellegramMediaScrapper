import os
import sys
import json
import datetime
import time
import asyncio
from telethon.sync import TelegramClient
from telethon import errors
from pytz import timezone
import re
from credentials import api_id, api_hash

def sanitize_filename(filename):
    return re.sub(r'[\/:*?"<>|]', '_', filename)

def serialize_datetime(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    else:
        return str(obj)

async def main():
    client = TelegramClient('session_name', api_id, api_hash)
    await client.start()
    
    if not await client.is_user_authorized():
        print('Connection to Telegram API failed!')
        sys.exit()
    
    print('Connection to Telegram API successful!')
    
    async def createChannelFolder(channel_name):
        folder_name = os.path.join('media', sanitize_filename(channel_name))
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        return folder_name

    async def downloadMedia(channel_folder, message):
        if hasattr(message, 'file') and message.file:
            mime_type = message.file.mime_type
            if 'image/' in mime_type:
                file_extension = mime_type.split('/')[-1]
            elif 'video/' in mime_type:
                file_extension = mime_type.split('/')[-1]
            else:
                file_extension = 'unknown'
            file_name = f"{channel_folder}/{sanitize_filename(str(message.id))}_{sanitize_filename(str(message.date))}.{file_extension}"

            if os.path.exists(file_name):
                print(f"Skipping file: {file_name} (already exists)")
                return

            await client.download_media(message, file_name)
        else:
            print(f"Skipped a message without a file: {message.id}")


    async def getTotalMediaSize(messages):
        total_size = 0
        media_messages = [message for message in messages if hasattr(message, 'file')]
        media_ids = [message.id for message in media_messages]

        for i in range(0, len(media_ids), 100):
            chunk = media_ids[i:i + 100]
            media_details = await client.get_messages(channel_entity, ids=chunk)
            for media_detail in media_details:
                if media_detail.file is not None:
                    total_size += media_detail.file.size
        return total_size

    async def fileCount():
        first_run = True
        if first_run:
            total_files = 0
            print('Counting the amount of files in the channel...')
            async for message in client.iter_messages(channel_entity):
                if hasattr(message, 'photo') or (hasattr(message, 'media') and hasattr(message.media, 'document') and 'video' in message.media.document.mime_type):
                    total_files += 1
            print('Number of files in the channel:', total_files)
            first_run = False
            return total_files
        else:
            pass

    def progress(current, total_files, total):
        last_update_time = time.time()
        if round(current / total * 100, 1) % 1.5 == 0 or time.time() - last_update_time >= 1.5:
            last_update_time = time.time()
            os.system('cls' if os.name == 'nt' else 'clear')
            print('Downloading the photos and videos in the channel between the chosen dates...')
            print('Downloaded', current, 'out of', total, '\n', current / total * 100, '%')

    my_channels = await client.get_dialogs()

    print('Your channels:')
    for dialog in my_channels:
        if dialog.is_channel:
            print(dialog.name)
            
    channel_name = input('Enter the name of the channel you want to connect to: ')
    channel_entity = None
    
    for dialog in my_channels:
        if dialog.name == channel_name:
            channel_entity = dialog.entity
            break

    if not channel_entity:
        print('Channel not found in your subscriptions.')
        await client.disconnect()
        sys.exit()
    
    channel_folder = await createChannelFolder(channel_name)

    date_start = input('Enter the start date (in format YYYY-MM-DD): ')
    date_end = input('Enter the end date (in format YYYY-MM-DD): ')
    
    date_start = datetime.datetime.strptime(date_start, '%Y-%m-%d').replace(tzinfo=timezone('UTC'))
    date_end = datetime.datetime.strptime(date_end, '%Y-%m-%d').replace(tzinfo=timezone('UTC'))
    
    print('Start date:', date_start)
    print('End date:', date_end)
    
    total_files = await fileCount()
    current_file_count = 0

    async def get_messages():
        messages = []
        print('Getting messages...')
        async for message in client.iter_messages(channel_entity, offset_date=date_start, reverse=True):
            if hasattr(message, 'photo') or (hasattr(message, 'media') and hasattr(message.media, 'document') and 'video' in message.media.document.mime_type):
                if message.date.replace(tzinfo=timezone('UTC')) < date_end:
                    break
                messages.append(message)
        print('Number of messages:', len(messages))        
        return messages
    
    print('Getting all the messages from the channel from date X to date Y...')
    messages = await get_messages()
    totalMediaSize = await getTotalMediaSize(messages)
    print('Total size of the photos and videos in the channel: {} bytes'.format(totalMediaSize))
    print('Creating a list with the following columns: date, time, sender, message, media (if any)...')
    data = []
    size = 0
        
    for message in messages:
        if hasattr(message, 'file') and message.file is not None:
            size += message.file.size
            data.append({
                'date': message.date,
                'time': message.date,
                'sender': message.sender_id,
                'message': message.message,
                'media': message.media
            })
        
    print('Calculating the size of the photos and videos in the channel...')
    print('Size of the photos and videos in the channel: {} bytes'.format(size))
    
    download = input('Do you want to download them? (Y/N): ')

    while download.lower() not in ['y', 'n']:
        print('Please enter a valid input!')
        download = input('Do you want to download them? (Y/N): ')

    if download.lower() == 'y':
        print('Downloading the photos and videos in the channel between the chosen dates...')
        
        for message in messages:
            try:
                if hasattr(message, 'file'):
                    await downloadMedia(channel_folder, message)
                    current_file_count += 1
                    progress(current_file_count, total_files, len(messages))
            except errors.rpcerrorlist.FileReferenceExpiredError:
                print(f"Skipped a message due to FileReferenceExpiredError: {message.id}")

        print('Download completed!')
        print('Saving the list in a .json file...')
        
        with open('data.json', 'w') as outfile:
            json.dump(data, outfile, default=serialize_datetime)
        
        print('File saved!')
    elif download.lower() == 'n':
        print('Exiting the script...')
    else:
        print('Please enter a valid input!')
    
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())