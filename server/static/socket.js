// shared WebSocket logic, imported by both sender.html and receiver.html.
// each page calls connect() with its own onMessage callback.
let socket;

function connect(onMessage) {
    // build the WebSocket URL from the current hostname so this works on any
    // network without hardcoding an IP address.
    socket = new WebSocket('ws://' + window.location.hostname + ':8080/ws');

    // check for succesful connection and print in console
    socket.addEventListener('open', function() {
        console.log('Connected to server!');
    });
    // listen for error and print to console
    socket.addEventListener('error', function(error) {
        console.log('WebSocket error:', error);
    });

    // if the connection drops, wait briefly and reconnect automatically.
    // passing onMessage through ensures the handler is re-registered each time.
    socket.addEventListener('close', function() {
        console.log('Connection lost. Reconnecting...');
        setTimeout(function() { connect(onMessage); }, 1000);
    });

    // sender passes no callback (it only sends).
    // receiver passes a function that updates the display when a message arrives.
    if (onMessage) {
        socket.addEventListener('message', onMessage);
    }
}