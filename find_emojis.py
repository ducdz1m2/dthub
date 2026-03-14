import os
import re

# Common emoji Unicode ranges
emoji_pattern = re.compile(
    '['
    '\U0001F600-\U0001F64F'  # emoticons
    '\U0001F300-\U0001F5FF'  # symbols & pictographs
    '\U0001F680-\U0001F6FF'  # transport & map symbols
    '\U0001F1E0-\U0001F1FF'  # flags
    '\U0001F900-\U0001F9FF'  # supplemental symbols
    '\U0001FA00-\U0001FA6F'  # chess symbols
    '\U0001FA70-\U0001FAFF'  # symbols and pictographs extended-a
    '\U00002702-\U000027B0'  # dingbats
    '\U000024C2-\U0001F251' 
    '\u2705'  # check mark
    '\u274c'  # cross mark
    '\u2b50'  # star
    '\u26a1'  # zap
    '\u23f3'  # hourglass
    '\u23f0'  # alarm clock
    '\u231b'  # hourglass done
    '\u2702'  # scissors
    '\u2600-\u26FF'  # miscellaneous symbols
    ']+',
    flags=re.UNICODE
)

# Single emojis to check
single_emojis = ['✅', '❌', '🔍', '📝', '🎤', '🛑', '🤖', '🔊', '⚙️', '🔤', '🆔', '🔧', '⚡', '📨', '🌐', '🔋', '📱', '🕒', '💡', '📤', '💾', '🔌', '🌡️', '🔔', '📶', '📡', '🎯', '📊', '🚀', '🏠', '⚠️', '❗', '🔎', '🔐', '🔑', '💻', '🖥️', '🖨️', '⌨️', '🖱️', '💽', '💿', '📀', '🎞️', '📽️', '🎬', '📺', '📷', '📸', '📹', '📼', '🔍', '🕯️', '💵', '💴', '💶', '💷', '💰', '💳', '💎', '⚖️', '🧰', '🔧', '🛠️', '🔨', '⚒️', '🛡️', '🔫', '🏹', '🛣️', '🗾', '🧭', '⏱️', '⏲️', '🕰️', '🌡️', '⛱️', '🗺️', '🧱', '🏗️', '⛰️', '🏔️', '🌋', '🗻', '🏕️', '⛺', '🏠', '🏡', '🏘️', '🏚️', '🏗️', '🏭', '🏢', '🏬', '🏣', '🏤', '🏥', '🏦', '🏨', '🏪', '🏫', '🏩', '💒', '🏛️', '⛪', '🕌', '🕍', '🛕', '🕋', '⛲', '⛺', '🌁', '🌃', '🏙️', '🌄', '🌅', '🌆', '🌇', '🌉', '♨️', '🎠', '🎡', '🎢', '💈', '🎪', '🛎️', '🚂', '🚃', '🚄', '🚅', '🚆', '🚇', '🚈', '🚉', '🚊', '🚝', '🚞', '🚋', '🚌', '🚍', '🚎', '🚐', '🚑', '🚒', '🚓', '🚔', '🚕', '🚖', '🚗', '🚘', '🚙', '🚚', '🚛', '🚜', '🏎️', '🏍️', '🛵', '🦽', '🦼', '🛺', '🚲', '🛴', '🚏', '🛣️', '🛤️', '🛢️', '⛽', '🚨', '🚥', '🚦', '🛑', '🚧', '⚓', '⛵', '🛶', '🚤', '🛳️', '⛴️', '🚢', '✈️', '🛩️', '🛫', '🛬', '🪂', '💺', '🚁', '🚟', '🚠', '🚡', '🛰️', '🚀', '🛸', '🛎️', '🧳', '⌚', '⏰', '⏱️', '⏲️', '🕰️', '🌡️', '🌞', '🌝', '🌛', '🌜', '🌚', '🌕', '🌖', '🌗', '🌘', '🌑', '🌒', '🌓', '🌔', '🌙', '🌎', '🌍', '🌏', '🪐', '💫', '⭐', '🌟', '✨', '⚡', '🔥', '💥', '☄️', '☀️', '🌤️', '⛅', '🌥️', '☁️', '🌦️', '🌧️', '⛈️', '🌩️', '🌨️', '❄️', '☃️', '⛄', '🌬️', '💨', '🌪️', '🌫️', '🌈', '☂️', '☔', '⚡', '❄️', '☃️', '⛄', '☄️', '🔥', '💧', '🌊']

found = False
for root, dirs, files in os.walk('ai_hub'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        for emoji in single_emojis:
                            if emoji in line:
                                print(f'{filepath}:{i}: {repr(line[:100])}')
                                found = True
                                break
            except Exception as e:
                print(f'Error reading {filepath}: {e}')

if not found:
    print('No emojis found in Python files')
