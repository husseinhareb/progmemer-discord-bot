from random import choice, randint


def get_response(user_input: str) -> str:
    lowered: str = user_input.lower()

    if lowered == '':
        return 'whats that...'
    elif 'hello' in lowered:
        return 'Hello there!'
    elif 'sup bro' in lowered:
        return 'nothing much what about you?'
    elif 'bye' in lowered:
        return 'bye !'
    elif 'roll dice' in lowered:
        return f'You rolled: {randint(1, 6)}'
    elif '$meme' in lowered:
        return 'right on it'
    else:
        return choice(['I do not understand...',
                       'What are you talking about?',
                       'Do you mind rephrasing that?'])