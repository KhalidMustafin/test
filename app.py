from flask import Flask, render_template, jsonify, request, url_for
from flask_socketio import SocketIO, emit, join_room
from random import choices, randint
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*")

games = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/game/<game_id>')
def game(game_id):
    if game_id not in games:
        games[game_id] = {
            'players': [],
            'board': generate_board(),
            'results': [],
            'timer': 9,
            'timer_active': False,
            'player_clicks': {}
        }
    return render_template('game.html', game_id=game_id)

@app.route('/invite/<game_id>')
def invite(game_id):
    if game_id in games:
        return jsonify({'url': url_for('game', game_id=game_id, _external=True)})
    return jsonify({'error': 'Игра не найдена'}), 404

@socketio.on('join_game')
def join_game(data):
    game_id = data['game_id']
    if game_id in games:
        join_room(game_id)
        if request.sid not in games[game_id]['players']:
            games[game_id]['players'].append(request.sid)
        print(f"Игрок присоединился к игре: {game_id}")
        emit('update_board', games[game_id]['board'], room=game_id)
        if not games[game_id]['timer_active']:
            games[game_id]['timer_active'] = True
            emit('timer_start', games[game_id]['timer'], room=game_id)
            socketio.start_background_task(timer_decrement, game_id)

@socketio.on('cell_click')
def cell_click(data):
    game_id = data['game_id']
    cell_index = data['cell']
    player_name = request.sid  # Здесь можно использовать идентификатор игрока или имя
    if game_id in games:
        if player_name in games[game_id]['player_clicks'] or games[game_id]['timer_active'] == False:
            return  # Игрок уже сделал выбор
        games[game_id]['player_clicks'][player_name] = True
        result = games[game_id]['board'][cell_index]
        games[game_id]['results'].append(result)
        emit('cell_result', {'cell_index': cell_index, 'result': result, 'player_name': player_name}, room=game_id)

@socketio.on('start_timer')
def start_timer(data):
    game_id = data['game_id']
    if game_id in games:
        games[game_id]['timer'] = 20
        socketio.start_background_task(timer_decrement, game_id)

def timer_decrement(game_id):
    while game_id in games and games[game_id]['timer'] > 0:
        socketio.sleep(1)
        games[game_id]['timer'] -= 1
        socketio.emit('timer_update', games[game_id]['timer'], room=game_id)
    if game_id in games:
        socketio.emit('game_over', games[game_id]['board'], room=game_id)
        games[game_id]['timer_active'] = False

def generate_board():
    symbols = ['💨', '🐹', '🐹', '🐹']
    weights = [75, 10, 10, 5]
    board = ['💨' for _ in range(9)]
    selected_indices = choices(range(9), k=4)
    for index in selected_indices:
        board[index] = choices(symbols, weights)[0]
    return board

if __name__ == "__main__":
    socketio.run(app, debug=True)
