from aiogram.fsm.state import State, StatesGroup


class GenerationState(StatesGroup):
    choosing_type = State()
    choosing_character = State()
    waiting_prompt = State()
    waiting_image = State()
    waiting_video = State()
