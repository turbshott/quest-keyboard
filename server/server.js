// import websocket, express, and http modules
const WebSocket = require('ws');
const express = require('express');
const http = require('http');

// initialize express app adn server
const app = express();
app.use (express.static('../client'));
const httpServer = http.createServer(app);
const wss = new WebSocket.Server({ server: httpServer });

// check and print server startup errors
wss.on('error', function(error) {
  console.log('Server failed to start:', error.message);
});

// initialize variable to store last message
let lastMessage = '';

// connect new client
wss.on('connection', function(socket) {
  console.log('A client connected');
  // relay last message to new clients that connect after a message was sent
  if (lastMessage) {
    socket.send(lastMessage);
  }

  // send message recieved from client
  socket.on('message', function(message) {

    // check for null messages and ignore them
    if (!message) {
      console.log('Received empty message — ignoring');
      return;
    }
    // update lastMessage with the new message
    lastMessage = message.toString();

    // log received message to console
    console.log('Received:', lastMessage);

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

// start http server on port 8080
httpServer.listen(8080, function() {
  console.log('Server running on port 8080');
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