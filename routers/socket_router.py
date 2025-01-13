from flask_socketio import join_room
from flask import current_app as app

def init_socket_routes(socketio):
    @socketio.on("register_client")
    def handle_client_registration(data):
        client_id = data.get("clientId")
        if client_id:
            join_room(client_id)
            app.logger.info(f"Client registered: {client_id}")