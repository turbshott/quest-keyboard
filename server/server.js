// import websocket (Claude Idea)
const WebSocket = require('ws');

// create websocket server on port 8080
const wss = new WebSocket.Server({ port: 8080 });

// check server start
wss.on('listening', function() {
  console.log('WebSocket server running on port 8080');
});

// check and print server startup errors
wss.on('error', function(error) {
  console.log('Server failed to start:', error.message);
});

// connect new client
wss.on('connection', function(socket) {
  console.log('A client connected');

  // send message recieved from client
  socket.on('message', function(message) {

    // check for null messages and ignore them
    if (!message) {
      console.log('Received empty message — ignoring');
      return;
    }

    // log received message to console
    console.log('Received:', message.toString());

    // send message to all other connected clients
    // to be updated with rooms/account logic in the future
    // loop through all clients and send the message to each one except the sender
    wss.clients.forEach(function(client) {
      if (client !== socket && client.readyState === WebSocket.OPEN) {
        // try sending with 3 attempts in case of transient errors
        // defined at bottom of this file
        trySend(client, message.toString(), 3);
      }
    });
  });

  // catch-all for any errors on the client socket
  socket.on('error', function(error) {
    console.log('Connection error:', error.message);
  });

  // log client disconnection
  socket.on('close', function() {
    console.log('A client disconnected');
  });
});

// trySend function with retry logic for sending messages to clients
function trySend(client, message, attemptsLeft) {
  try {
    client.send(message);
  } catch (error) {
    if (attemptsLeft > 1) {
      console.log('Send failed, retrying... (' + (attemptsLeft - 1) + ' attempt(s) left)');
      setTimeout(function() {
        trySend(client, message, attemptsLeft - 1);
      }, 500);
    } else {
      console.log('Message failed to send after all attempts:', error.message);
    }
  }
}