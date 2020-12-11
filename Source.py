import random
import time
import threading
import readchar
import sys
from collections import Counter
from firebase import firebase


GRID_SIZE_HORIZONTAL = 7
GRID_SIZE_VERTICAL = 5
VOWEL_SPLIT = int(2 / 5 * GRID_SIZE_VERTICAL)

ROTATION_TIME = 7
GAME_TIME = 30

english_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
english_vowels = ['A', 'E', 'I', 'O', 'U']

points = {'A': 1, 'B': 3, 'C': 3, 'D': 2, 'E': 1, 'F': 4, 'G': 2, 'H': 4, 'I': 1, 'J': 8, 'K': 5, 'L': 1, 'M': 3, 'N': 1, 'O': 1, 'P': 3, 'Q': 10, 'R': 1, 'S': 1, 'T': 1, 'U': 1, 'V': 4, 'W': 4, 'X': 8, 'Y': 4, 'Z': 10}


def load_words():
    with open('words_alpha.txt') as word_file:
        valid_words = set(word_file.read().split())
    return valid_words


english_dictionary = load_words()


def select_letters_for_game():
    def select_three_letters():
        _letters = []
        for _ in range(GRID_SIZE_VERTICAL - VOWEL_SPLIT):
            _letters.append(english_letters[random.randint(0, 25)])
        for _ in range(VOWEL_SPLIT):
            _letters.append(english_vowels[random.randint(0, 4)])
        random.shuffle(_letters)
        return _letters

    letters = []
    for _ in range(GAME_TIME // ROTATION_TIME + GRID_SIZE_HORIZONTAL):
        letters.append(select_three_letters())
    return letters


def is_word_viable():
    global letters_to_display, characters_in_stream
    letters = Counter(''.join([''.join(_letters) for _letters in letters_to_display]))
    letters.subtract(Counter(characters_in_stream))
    return all(v >= 0 for v in letters.values())


def check_words(words):
    return set([word for word in words if word and word in english_dictionary])


def check_points(words):
    word_points = [sum([points[char] for char in word]) for word in words]
    return sum(word_points), max(word_points)


def display_letters():
    def _display_letters(letters_to_display):
        global characters_in_stream
        print('\033c')
        for i, column in enumerate(letters_to_display):
            for ii, letter in enumerate(column):
                print('\033[{};{}H{}'.format(ii * 2 + 2,  i * 2 + 2, letter))
        print('\033[{};{}H'.format((GRID_SIZE_VERTICAL + 1) * 2, 0))
        sys.stdout.write(characters_in_stream)
        sys.stdout.flush()
    def rotate_letters():
        global letters, letters_to_display
        for index in range(len(letters) - GRID_SIZE_HORIZONTAL + 1):
            letters_to_display = letters[index: index + GRID_SIZE_HORIZONTAL]
            yield letters_to_display
    global is_display_rotated_done
    for _letters_to_display in rotate_letters():
        _display_letters(_letters_to_display)
        time.sleep(ROTATION_TIME)
    is_display_rotated_done = True
    sys.stdout.write('Press enter when you see this message.\n')
    sys.stdout.flush()
    sys.stdin.flush()


class Player:
    def __init__(self, name, score = 0, word_list = [], word_count = 0, max_points = 0, longest_word_length = ''):
        self.name = name
        self.score = score
        self.word_list = word_list
        self.word_count = word_count
        self.max_points = max_points
        self.longest_word_length = longest_word_length

    def calculate_score(self):
        if self.score == 0:
            self.word_list = check_words(self.word_list)
            if self.word_list:
                self.longest_word_length = max(len(word) for word in self.word_list)
                self.score, self.max_points = check_points(self.word_list)
                self.word_list = list(self.word_list)
                self.word_count = len(self.word_list)

    def __str__(self):
        self.calculate_score()
        return '{}: {} points, {} words, maximum points: {}, maximum length: {}\n{}'\
            .format(self.name, self.score, self.word_count, self.max_points, self.longest_word_length, self.word_list)


letters_to_display = []
letters = []
# is_single_player = input('Do you want to play single player? y/n')
is_single_player = 'n'
db = None
game_number = '1000' # todo make simple input to choose game_number if joining game, given game_number if host to allow multi simultaneous games
if is_single_player == 'y':
    letters = select_letters_for_game()
else:
    db = firebase.FirebaseApplication('https://movingscramble.firebaseio.com/', None)
    db.delete('/', None)
    is_host = input('Are you a host? y/n')
    if is_host == 'y':
        letters = select_letters_for_game()
        db.post('/letters/A{}'.format(game_number), letters)
    else:
        # game_number = str(input('Enter game number: '))  # assume 1000 for now
        letters_online = db.get('/letters/', 'A{}'.format(game_number))
        letters_online_list = []
        for values in letters_online.values():
            letters_online_list_inner = []
            for value in values:
                letters_online_list_inner.append(value)
            letters_online_list.append(letters_online_list_inner)
        letters = letters_online_list[0]
name = ''
try:
    with open('name.txt', 'r', encoding='utf-8') as f:
        name = f.read()
except FileNotFoundError:
    name = input('Enter your name: ')
    with open('name.txt', 'w', encoding='utf-8') as f:
        f.write(name)
player = Player(name)
input('Press enter when everyone is ready.')
threading.Thread(target=display_letters).start()
is_display_rotated = False
is_display_rotated_done = False
characters_in_stream = ''
while True:
    getch = readchar.readchar() # best to use separate implementations for windows and linux/mac and include timeout to read input
    if is_display_rotated_done:
        break
    sys.stdout.write(getch)
    sys.stdout.flush()
    if getch == '\r':
        characters_in_stream = characters_in_stream.upper()
        if is_word_viable():
            player.word_list.append(characters_in_stream)
        characters_in_stream = ''
        print('\033[{0};{1}H{2}\033[{0};{1}H'.format((GRID_SIZE_VERTICAL + 1) * 2 + 1, 0, ' ' * 20), end='')
        sys.stdout.flush()
    elif getch == readchar.key.BACKSPACE:
        print('\033[{0};{1}H \033[{0};{1}H'.format((GRID_SIZE_VERTICAL + 1) * 2 + 1, len(characters_in_stream)), end='')
        sys.stdout.flush()
        characters_in_stream = characters_in_stream[:-1]
    elif getch == '\x03':
        break
    else:
        characters_in_stream += getch
print('Time is up!\n\nYour profile:\n{}'.format(player))
if is_single_player == 'y':
    exit()
print('\nFetching players\' profiles...')
data = vars(player)
db.post('/games/A{}'.format(game_number), data)
time.sleep(10)  # long enough for most people's internet to catch up... most of the time!
results = db.get('/games/', 'A{}'.format(game_number))
players = []
for key in results.keys():
    players.append(Player(**results[key]))
print('\033c')
for player in players:
    print('{}\n'.format(player))
