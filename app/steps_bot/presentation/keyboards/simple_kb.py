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

phone_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='📱 Поделиться номером телефона', request_contact=True)]
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder='Пожалуйста, поделитесь своим номером телефона'
)

location_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='📍 Поделиться локацией', request_location=True)]
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder='Пожалуйста, поделитесь своей локацией'
)

walk_choice = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='Гуляю с собакой', callback_data='dog_walk')],
        [InlineKeyboardButton(text='Гуляю с коляской', callback_data='stroller_walk')],
        [InlineKeyboardButton(text='Гуляю c собакой и коляской', callback_data='both_walk')],
        [InlineKeyboardButton(text='↩', callback_data='back')]
    ]
)

end_walk_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Завершить прогулку', callback_data='end_walk')]
])

