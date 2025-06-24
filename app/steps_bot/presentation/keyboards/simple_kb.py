from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

main_menu_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='Начать прогулку', callback_data='walk')],
        [InlineKeyboardButton(text='Ваша семья', callback_data='family')],
        [InlineKeyboardButton(text='Баланс', callback_data='balance')],
        [InlineKeyboardButton(text='Каталог', callback_data='catalog')],
        [InlineKeyboardButton(text='FAQ', callback_data='faq')],
        [InlineKeyboardButton(text='Техническая поддержка', url='https://t.me/bottecp')]
    ]
)

back_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='↩', callback_data='back')]
    ]
)

phone_request_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='📱 Поделиться номером телефона', request_contact=True)]
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder='Пожалуйста, поделитесь своим номером телефона'
)


analitic_reports = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='Ежеквартальный отчет MARKETBEAT', callback_data='reports')],  # TODO: будут дженерик клавы открываться на кварталы 
        [InlineKeyboardButton(text='Обзоры по сегментам рынка', callback_data='reviews')],  # TODO: будут дженерик клавы открываться на (склады, инвестиции итд)
        [InlineKeyboardButton(text='↩', callback_data='back')]
    ]
)
