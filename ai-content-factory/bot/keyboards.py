from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


CONTENT_TYPE_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🖼 Image", callback_data="type:image")],
        [InlineKeyboardButton(text="🎥 Video", callback_data="type:video")],
    ]
)

CHARACTER_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Olivia", callback_data="char:olivia")],
        [InlineKeyboardButton(text="Jasmine", callback_data="char:jasmine")],
    ]
)
